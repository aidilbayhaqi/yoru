import uuid
from datetime import datetime

from sqlalchemy import Select, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.models import AuditEvent
from yoru_api.modules.identity.models import (
    AuthSession,
    Partner,
    PartnerMembership,
    Permission,
    RefreshTokenHistory,
    Role,
    RolePermission,
    User,
    UserCredential,
    UserPlatformRole,
)
from yoru_api.modules.identity.permissions import Actor, MembershipContext


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_credentials(
        self, email: str
    ) -> tuple[User, UserCredential] | None:
        statement = (
            select(User, UserCredential)
            .join(UserCredential, UserCredential.user_id == User.id)
            .where(User.email == email)
        )
        result = await self._session.execute(statement)
        row = result.one_or_none()
        return (row[0], row[1]) if row else None

    async def add_customer(
        self,
        *,
        email: str,
        full_name: str,
        password_hash: str,
    ) -> User:
        user = User(email=email, full_name=full_name, status="active")
        self._session.add(user)
        await self._session.flush()
        self._session.add(UserCredential(user_id=user.id, password_hash=password_hash))
        return user

    async def add_session(self, auth_session: AuthSession) -> None:
        self._session.add(auth_session)
        await self._session.flush()

    async def find_session_by_access_hash(
        self, token_hash: str, *, for_update: bool = False
    ) -> AuthSession | None:
        statement: Select[tuple[AuthSession]] = select(AuthSession).where(
            AuthSession.access_token_hash == token_hash
        )
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def find_session_by_refresh_hash(
        self, token_hash: str, *, for_update: bool = False
    ) -> AuthSession | None:
        statement: Select[tuple[AuthSession]] = select(AuthSession).where(
            AuthSession.refresh_token_hash == token_hash
        )
        if for_update:
            statement = statement.with_for_update()
        return await self._session.scalar(statement)

    async def find_session_by_refresh_history(
        self, token_hash: str
    ) -> AuthSession | None:
        statement = (
            select(AuthSession)
            .join(RefreshTokenHistory, RefreshTokenHistory.session_id == AuthSession.id)
            .where(RefreshTokenHistory.token_hash == token_hash)
            .with_for_update(of=AuthSession)
        )
        return await self._session.scalar(statement)

    def add_refresh_history(
        self,
        *,
        session_id: uuid.UUID,
        token_hash: str,
        consumed_at: datetime,
    ) -> None:
        self._session.add(
            RefreshTokenHistory(
                session_id=session_id,
                token_hash=token_hash,
                consumed_at=consumed_at,
            )
        )

    async def revoke_family(
        self,
        *,
        family_id: uuid.UUID,
        revoked_at: datetime,
        reason: str,
    ) -> None:
        await self._session.execute(
            update(AuthSession)
            .where(AuthSession.family_id == family_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at, revoke_reason=reason)
        )

    async def revoke_all_user_sessions(
        self,
        *,
        user_id: uuid.UUID,
        revoked_at: datetime,
        reason: str,
        except_session_id: uuid.UUID | None = None,
    ) -> None:
        statement = update(AuthSession).where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        if except_session_id is not None:
            statement = statement.where(AuthSession.id != except_session_id)
        await self._session.execute(
            statement.values(revoked_at=revoked_at, revoke_reason=reason)
        )

    async def revoke_session(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        revoked_at: datetime,
        reason: str,
    ) -> bool:
        auth_session = await self._session.scalar(
            select(AuthSession)
            .where(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .with_for_update()
        )
        if auth_session is None:
            return False
        auth_session.revoked_at = revoked_at
        auth_session.revoke_reason = reason
        return True

    async def list_user_sessions(self, user_id: uuid.UUID) -> list[AuthSession]:
        result = await self._session.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .order_by(AuthSession.last_used_at.desc(), AuthSession.id.desc())
        )
        return list(result)

    async def _role_permissions(
        self,
        *,
        user_id: uuid.UUID,
    ) -> tuple[frozenset[str], frozenset[str]]:
        statement = (
            select(Role.code, Permission.code)
            .join(UserPlatformRole, UserPlatformRole.role_id == Role.id)
            .outerjoin(RolePermission, RolePermission.role_id == Role.id)
            .outerjoin(Permission, Permission.id == RolePermission.permission_id)
            .where(UserPlatformRole.user_id == user_id)
        )
        rows = (await self._session.execute(statement)).all()
        roles = frozenset(row[0] for row in rows)
        permissions = frozenset(row[1] for row in rows if row[1] is not None)
        return roles, permissions

    async def _set_rls_context(
        self,
        *,
        user_id: uuid.UUID,
        partner_id: uuid.UUID | None,
        is_platform_admin: bool,
    ) -> None:
        await self._session.execute(
            text(
                """
                SELECT
                    set_config('app.user_id', :user_id, true),
                    set_config('app.partner_id', :partner_id, true),
                    set_config('app.is_platform_admin', :is_platform_admin, true)
                """
            ),
            {
                "user_id": str(user_id),
                "partner_id": str(partner_id) if partner_id else "",
                "is_platform_admin": "true" if is_platform_admin else "false",
            },
        )

    async def build_actor(self, auth_session: AuthSession) -> Actor | None:
        user = await self._session.get(User, auth_session.user_id)
        if user is None:
            return None

        platform_roles, platform_permissions = await self._role_permissions(user_id=user.id)
        await self._set_rls_context(
            user_id=user.id,
            partner_id=auth_session.active_partner_id,
            is_platform_admin=bool(platform_roles),
        )

        statement = (
            select(
                PartnerMembership.partner_id,
                Partner.status,
                PartnerMembership.status,
                Role.code,
                Permission.code,
            )
            .join(Partner, Partner.id == PartnerMembership.partner_id)
            .join(Role, Role.id == PartnerMembership.role_id)
            .outerjoin(RolePermission, RolePermission.role_id == Role.id)
            .outerjoin(Permission, Permission.id == RolePermission.permission_id)
            .where(PartnerMembership.user_id == user.id)
            .order_by(PartnerMembership.partner_id)
        )
        rows = (await self._session.execute(statement)).all()
        memberships_by_id: dict[
            uuid.UUID, tuple[str, str, str, set[str]]
        ] = {}
        for row in rows:
            membership = memberships_by_id.get(row[0])
            if membership is None:
                membership = (row[1], row[2], row[3], set())
                memberships_by_id[row[0]] = membership
            if row[4] is not None:
                membership[3].add(row[4])

        memberships = tuple(
            MembershipContext(
                partner_id=partner_id,
                partner_status=partner_status,
                membership_status=membership_status,
                role=role,
                permissions=frozenset(permissions),
            )
            for partner_id, (
                partner_status,
                membership_status,
                role,
                permissions,
            ) in memberships_by_id.items()
        )
        return Actor(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            session_id=auth_session.id,
            active_partner_id=auth_session.active_partner_id,
            platform_roles=platform_roles,
            platform_permissions=platform_permissions,
            memberships=memberships,
            mfa_verified_at=auth_session.mfa_verified_at,
        )

    async def set_active_partner(
        self,
        *,
        auth_session: AuthSession,
        partner_id: uuid.UUID | None,
    ) -> None:
        auth_session.active_partner_id = partner_id
        await self._session.flush()

    def add_audit(
        self,
        *,
        actor_id: uuid.UUID | None,
        partner_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self._session.add(
            AuditEvent(
                actor_id=actor_id,
                partner_id=partner_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                event_metadata=metadata or {},
            )
        )

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
