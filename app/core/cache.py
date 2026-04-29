import time
import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Channel, ModelPool, PoolMember, Token
from app.config import settings

CACHE_TTL = settings.channel_cache_ttl  # seconds

_cache: dict[str, Any] = {}
_expiry: dict[str, float] = {}
_lock = asyncio.Lock()


def _is_expired(key: str) -> bool:
    return key not in _expiry or time.time() > _expiry[key]


async def _get_or_load(key: str, loader) -> Any:
    """通用缓存加载器。"""
    if not _is_expired(key):
        return _cache.get(key)
    async with _lock:
        # double-check
        if not _is_expired(key):
            return _cache.get(key)
        data = await loader()
        _cache[key] = data
        _expiry[key] = time.time() + CACHE_TTL
        return data


async def get_token_by_key(db: AsyncSession, key: str) -> Token | None:
    """按 key 缓存 Token。"""
    cache_key = f"token:{key}"

    async def _load():
        result = await db.execute(select(Token).where(Token.key == key, Token.status == 1))
        return result.scalar_one_or_none()

    return await _get_or_load(cache_key, _load)


async def get_all_channels(db: AsyncSession) -> list[Channel]:
    """缓存所有启用的 Channel。"""
    cache_key = "channels:all"

    async def _load():
        result = await db.execute(select(Channel).where(Channel.status == 1))
        return list(result.scalars().all())

    return await _get_or_load(cache_key, _load)


async def get_all_pools(db: AsyncSession) -> list[ModelPool]:
    """缓存所有启用的 Pool。"""
    cache_key = "pools:all"

    async def _load():
        result = await db.execute(select(ModelPool).where(ModelPool.status == 1))
        return list(result.scalars().all())

    return await _get_or_load(cache_key, _load)


async def get_pool_members(db: AsyncSession, pool_id: int) -> list[PoolMember]:
    """缓存指定 Pool 的成员。"""
    cache_key = f"pool_members:{pool_id}"

    async def _load():
        result = await db.execute(
            select(PoolMember)
            .where(PoolMember.pool_id == pool_id, PoolMember.status == 1)
            .order_by(PoolMember.priority, PoolMember.weight.desc())
        )
        return list(result.scalars().all())

    return await _get_or_load(cache_key, _load)


def invalidate(key_prefix: str | None = None):
    """失效缓存。key_prefix 为 None 时清除全部。"""
    global _cache, _expiry
    if key_prefix is None:
        _cache.clear()
        _expiry.clear()
    else:
        keys_to_remove = [k for k in _cache if k.startswith(key_prefix)]
        for k in keys_to_remove:
            _cache.pop(k, None)
            _expiry.pop(k, None)


def invalidate_token(key: str):
    """失效指定 Token 缓存。"""
    _cache.pop(f"token:{key}", None)
    _expiry.pop(f"token:{key}", None)


def invalidate_channels():
    """失效 Channel 缓存。"""
    invalidate("channels:")


def invalidate_pools():
    """失效 Pool 缓存。"""
    invalidate("pools:")
    invalidate("pool_members:")


def invalidate_all():
    """清除所有缓存。"""
    invalidate(None)
