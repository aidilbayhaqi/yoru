import hashlib
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from yoru_api.core.problem import AppError
from yoru_api.core.settings import Settings
from yoru_api.modules.identity.security import normalize_email

logger = logging.getLogger("yoru_api.auth")


class LoginRateLimiter:
    def __init__(self, settings: Settings) -> None:
        self._client = Redis.from_url(settings.redis_url, decode_responses=True)
        self._attempts = settings.auth_rate_limit_attempts
        self._window_seconds = settings.auth_rate_limit_window_seconds

    def _key(self, *, ip_address: str, email: str) -> str:
        identity = f"{ip_address}:{normalize_email(email)}"
        digest = hashlib.sha256(identity.encode()).hexdigest()
        return f"yoru:auth:login:{digest}"

    async def check(self, *, ip_address: str, email: str) -> None:
        key = self._key(ip_address=ip_address, email=email)
        try:
            count = await self._client.incr(key)
            if count == 1:
                await self._client.expire(key, self._window_seconds)
        except RedisError as error:
            logger.exception("auth_rate_limit_unavailable")
            raise AppError(
                503,
                "AUTH_PROTECTION_UNAVAILABLE",
                "Authentication protection is temporarily unavailable",
            ) from error
        if count > self._attempts:
            raise AppError(
                429,
                "AUTH_RATE_LIMITED",
                "Too many authentication attempts",
            )

    async def clear(self, *, ip_address: str, email: str) -> None:
        try:
            await self._client.delete(self._key(ip_address=ip_address, email=email))
        except RedisError:
            logger.warning("auth_rate_limit_clear_failed")

    async def close(self) -> None:
        await self._client.aclose()
