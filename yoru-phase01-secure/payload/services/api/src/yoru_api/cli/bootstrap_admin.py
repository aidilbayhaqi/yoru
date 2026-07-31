import argparse
import asyncio
import getpass

from sqlalchemy import select

from yoru_api.core.database import create_database_engine, create_session_factory
from yoru_api.core.problem import AppError
from yoru_api.core.settings import get_settings
from yoru_api.modules.identity.models import Role, UserPlatformRole
from yoru_api.modules.identity.repository import IdentityRepository
from yoru_api.modules.identity.schemas import RegisterRequest
from yoru_api.modules.identity.security import hash_password, normalize_email


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Yoru super admin without exposing a public admin register."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    return parser.parse_args()


async def bootstrap_admin(*, email: str, full_name: str, password: str) -> None:
    payload = RegisterRequest(email=email, full_name=full_name, password=password)
    settings = get_settings()
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            repository = IdentityRepository(session)
            normalized_email = normalize_email(str(payload.email))
            if await repository.get_user_credentials(normalized_email) is not None:
                raise AppError(409, "ACCOUNT_EXISTS", "Account already exists")
            role = await session.scalar(select(Role).where(Role.code == "super_admin"))
            if role is None:
                raise RuntimeError("super_admin role is missing; run Alembic migration first")
            encoded_password = await asyncio.to_thread(hash_password, payload.password)
            user = await repository.add_customer(
                email=normalized_email,
                full_name=payload.full_name.strip(),
                password_hash=encoded_password,
            )
            session.add(UserPlatformRole(user_id=user.id, role_id=role.id))
            repository.add_audit(
                actor_id=user.id,
                partner_id=None,
                action="identity.super_admin_bootstrapped",
                resource_type="user",
                resource_id=str(user.id),
            )
            await repository.commit()
    finally:
        await engine.dispose()


def main() -> None:
    args = parse_args()
    password = getpass.getpass("Super admin password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    try:
        asyncio.run(
            bootstrap_admin(
                email=args.email,
                full_name=args.name,
                password=password,
            )
        )
    except AppError as error:
        raise SystemExit(error.title) from error
    print("Super admin created successfully.")


if __name__ == "__main__":
    main()
