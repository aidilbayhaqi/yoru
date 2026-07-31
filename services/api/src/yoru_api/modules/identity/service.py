import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from yoru_api.core.problem import AppError
from yoru_api.core.settings import Settings
from yoru_api.modules.identity.models import AuthSession, User
from yoru_api.modules.identity.permissions import Actor
from yoru_api.modules.identity.repository import IdentityRepository
from yoru_api.modules.identity.security import (
    TokenPair,
    hash_optional_metadata,
    hash_password,
    hash_token,
    new_token_pair,
    normalize_email,
    verify_password,
)


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    user: User
    auth_session: AuthSession
    actor: Actor
    tokens: TokenPair


class IdentityService:
    def __init__(self, repository: IdentityRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    @property
    def _access_secret(self) -> str:
        return self._settings.session_signing_key.get_secret_value()

    @property
    def _refresh_secret(self) -> str:
        return self._settings.refresh_token_pepper.get_secret_value()

    def _new_session(
        self,
        *,
        user_id: uuid.UUID,
        tokens: TokenPair,
        user_agent: str | None,
        ip_prefix: str | None,
    ) -> AuthSession:
        now = datetime.now(UTC)
        return AuthSession(
            user_id=user_id,
            family_id=uuid.uuid4(),
            access_token_hash=hash_token(tokens.access_token, self._access_secret),
            refresh_token_hash=hash_token(tokens.refresh_token, self._refresh_secret),
            access_expires_at=now
            + timedelta(seconds=self._settings.access_token_ttl_seconds),
            refresh_expires_at=now
            + timedelta(seconds=self._settings.refresh_token_ttl_seconds),
            user_agent_hash=hash_optional_metadata(user_agent),
            ip_prefix=ip_prefix,
            last_used_at=now,
        )

    async def _result(
        self,
        *,
        user: User,
        auth_session: AuthSession,
        tokens: TokenPair,
    ) -> AuthenticationResult:
        actor = await self._repository.build_actor(auth_session)
        if actor is None:
            raise AppError(401, "INVALID_SESSION", "Invalid session")
        return AuthenticationResult(
            user=user,
            auth_session=auth_session,
            actor=actor,
            tokens=tokens,
        )

    async def register_customer(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
        user_agent: str | None,
        ip_prefix: str | None,
    ) -> AuthenticationResult:
        normalized_email = normalize_email(email)
        if await self._repository.get_user_credentials(normalized_email) is not None:
            raise AppError(409, "ACCOUNT_EXISTS", "Account cannot be created")

        encoded_password = await asyncio.to_thread(hash_password, password)
        tokens = new_token_pair()
        try:
            user = await self._repository.add_customer(
                email=normalized_email,
                full_name=full_name.strip(),
                password_hash=encoded_password,
            )
            auth_session = self._new_session(
                user_id=user.id,
                tokens=tokens,
                user_agent=user_agent,
                ip_prefix=ip_prefix,
            )
            await self._repository.add_session(auth_session)
            self._repository.add_audit(
                actor_id=user.id,
                partner_id=None,
                action="identity.customer_registered",
                resource_type="user",
                resource_id=str(user.id),
            )
            await self._repository.commit()
        except IntegrityError as error:
            await self._repository.rollback()
            raise AppError(409, "ACCOUNT_EXISTS", "Account cannot be created") from error
        return await self._result(user=user, auth_session=auth_session, tokens=tokens)

    async def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None,
        ip_prefix: str | None,
    ) -> AuthenticationResult:
        normalized_email = normalize_email(email)
        record = await self._repository.get_user_credentials(normalized_email)
        valid = (
            record is not None
            and await asyncio.to_thread(
                verify_password,
                password,
                record[1].password_hash,
            )
        )
        if not valid or record is None or record[0].status != "active":
            raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password")

        user = record[0]
        tokens = new_token_pair()
        auth_session = self._new_session(
            user_id=user.id,
            tokens=tokens,
            user_agent=user_agent,
            ip_prefix=ip_prefix,
        )
        await self._repository.add_session(auth_session)
        self._repository.add_audit(
            actor_id=user.id,
            partner_id=None,
            action="identity.login_succeeded",
            resource_type="session",
            resource_id=str(auth_session.id),
        )
        await self._repository.commit()
        return await self._result(user=user, auth_session=auth_session, tokens=tokens)

    async def authenticate_access(self, access_token: str | None) -> Actor:
        if not access_token:
            raise AppError(401, "AUTHENTICATION_REQUIRED", "Authentication required")
        token_hash = hash_token(access_token, self._access_secret)
        auth_session = await self._repository.find_session_by_access_hash(token_hash)
        now = datetime.now(UTC)
        if (
            auth_session is None
            or auth_session.revoked_at is not None
            or auth_session.access_expires_at <= now
        ):
            raise AppError(401, "INVALID_SESSION", "Invalid or expired session")
        actor = await self._repository.build_actor(auth_session)
        if actor is None or actor.status != "active":
            raise AppError(401, "INVALID_SESSION", "Invalid or expired session")
        return actor

    async def refresh(
        self,
        *,
        refresh_token: str | None,
    ) -> tuple[Actor, TokenPair]:
        if not refresh_token:
            raise AppError(401, "INVALID_REFRESH_TOKEN", "Invalid refresh token")
        token_hash = hash_token(refresh_token, self._refresh_secret)
        auth_session = await self._repository.find_session_by_refresh_hash(
            token_hash, for_update=True
        )
        now = datetime.now(UTC)

        if auth_session is None:
            reused_session = await self._repository.find_session_by_refresh_history(
                token_hash
            )
            if reused_session is not None:
                await self._repository.revoke_family(
                    family_id=reused_session.family_id,
                    revoked_at=now,
                    reason="refresh_token_reuse",
                )
                self._repository.add_audit(
                    actor_id=reused_session.user_id,
                    partner_id=reused_session.active_partner_id,
                    action="identity.refresh_reuse_detected",
                    resource_type="session_family",
                    resource_id=str(reused_session.family_id),
                )
                await self._repository.commit()
            raise AppError(401, "INVALID_REFRESH_TOKEN", "Invalid refresh token")

        if (
            auth_session.revoked_at is not None
            or auth_session.refresh_expires_at <= now
        ):
            if auth_session.revoked_at is None:
                await self._repository.revoke_family(
                    family_id=auth_session.family_id,
                    revoked_at=now,
                    reason="refresh_expired",
                )
                await self._repository.commit()
            raise AppError(401, "INVALID_REFRESH_TOKEN", "Invalid refresh token")

        self._repository.add_refresh_history(
            session_id=auth_session.id,
            token_hash=auth_session.refresh_token_hash,
            consumed_at=now,
        )
        tokens = new_token_pair()
        auth_session.access_token_hash = hash_token(tokens.access_token, self._access_secret)
        auth_session.refresh_token_hash = hash_token(
            tokens.refresh_token, self._refresh_secret
        )
        auth_session.access_expires_at = now + timedelta(
            seconds=self._settings.access_token_ttl_seconds
        )
        auth_session.refresh_expires_at = now + timedelta(
            seconds=self._settings.refresh_token_ttl_seconds
        )
        auth_session.last_used_at = now
        await self._repository.commit()

        actor = await self._repository.build_actor(auth_session)
        if actor is None or actor.status != "active":
            raise AppError(401, "INVALID_SESSION", "Invalid session")
        return actor, tokens

    async def select_partner(
        self,
        *,
        actor: Actor,
        partner_id: uuid.UUID | None,
        access_token: str,
    ) -> Actor:
        if partner_id is not None and not any(
            membership.partner_id == partner_id
            and membership.membership_status == "active"
            for membership in actor.memberships
        ):
            raise AppError(403, "TENANT_SCOPE_DENIED", "Tenant scope denied")
        token_hash = hash_token(access_token, self._access_secret)
        auth_session = await self._repository.find_session_by_access_hash(
            token_hash, for_update=True
        )
        if auth_session is None or auth_session.id != actor.session_id:
            raise AppError(401, "INVALID_SESSION", "Invalid session")
        await self._repository.set_active_partner(
            auth_session=auth_session,
            partner_id=partner_id,
        )
        self._repository.add_audit(
            actor_id=actor.user_id,
            partner_id=partner_id,
            action="identity.active_partner_changed",
            resource_type="session",
            resource_id=str(actor.session_id),
        )
        await self._repository.commit()
        refreshed_actor = await self._repository.build_actor(auth_session)
        if refreshed_actor is None:
            raise AppError(401, "INVALID_SESSION", "Invalid session")
        return refreshed_actor

    async def logout(self, *, actor: Actor) -> None:
        revoked = await self._repository.revoke_session(
            session_id=actor.session_id,
            user_id=actor.user_id,
            revoked_at=datetime.now(UTC),
            reason="logout",
        )
        if revoked:
            self._repository.add_audit(
                actor_id=actor.user_id,
                partner_id=actor.active_partner_id,
                action="identity.logout",
                resource_type="session",
                resource_id=str(actor.session_id),
            )
        await self._repository.commit()

    async def logout_all(self, *, actor: Actor) -> None:
        await self._repository.revoke_all_user_sessions(
            user_id=actor.user_id,
            revoked_at=datetime.now(UTC),
            reason="logout_all",
        )
        self._repository.add_audit(
            actor_id=actor.user_id,
            partner_id=actor.active_partner_id,
            action="identity.logout_all",
            resource_type="user",
            resource_id=str(actor.user_id),
        )
        await self._repository.commit()

    async def revoke_session(
        self,
        *,
        actor: Actor,
        session_id: uuid.UUID,
    ) -> bool:
        revoked = await self._repository.revoke_session(
            session_id=session_id,
            user_id=actor.user_id,
            revoked_at=datetime.now(UTC),
            reason="user_revoked",
        )
        if not revoked:
            raise AppError(404, "SESSION_NOT_FOUND", "Session not found")
        self._repository.add_audit(
            actor_id=actor.user_id,
            partner_id=actor.active_partner_id,
            action="identity.session_revoked",
            resource_type="session",
            resource_id=str(session_id),
        )
        await self._repository.commit()
        return revoked

    async def list_sessions(self, actor: Actor) -> list[AuthSession]:
        return await self._repository.list_user_sessions(actor.user_id)
