import time
import asyncio
from typing import Dict, Any
from sqlalchemy import select, insert
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

# 扩展的健康状态数据结构
_channel_health: Dict[str, Dict[str, Any]] = {}

# 配置阈值
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_BASE_COOLDOWN = 60
CIRCUIT_MAX_COOLDOWN = 600
AUTO_DISABLE_THRESHOLD = 10  # 连续失败 10 次自动禁用
AUTO_RECOVERY_INTERVAL = 60  # 每 60 秒探测一次禁用渠道
HEALTH_SYNC_INTERVAL = 30  # 每 30 秒持久化到 SQLite

_dirty_keys: set[str] = set()

from app.database import SessionLocal
from app.models import HealthSnapshot


def health_key(channel_id: int, upstream_model: str | None = None) -> str:
    """Build a health key. Model-specific keys prevent one bad model from poisoning a channel."""
    return f"{channel_id}:{upstream_model}" if upstream_model else str(channel_id)


async def restore_health_from_db():
    """从数据库恢复健康状态（服务启动时调用）。"""
    try:
        async with SessionLocal() as session:
            result = await session.execute(select(HealthSnapshot))
            for row in result.scalars().all():
                # Check if cooldown is still valid
                now = time.time()
                cooldown = row.cooldown_until if row.cooldown_until > now else 0.0
                soft = row.soft_cooldown_until if row.soft_cooldown_until > now else 0.0
                # If both expired and no failures, skip
                if cooldown == 0 and soft == 0 and row.consecutive_failures == 0:
                    continue
                _channel_health[row.health_key] = {
                    "consecutive_failures": row.consecutive_failures,
                    "cooldown_until": cooldown,
                    "soft_cooldown_until": soft,
                    "last_error": row.last_error or "",
                    "total_requests": row.total_requests or 0,
                    "failed_requests": row.failed_requests or 0,
                    "last_success_time": row.last_success_time or 0,
                    "last_error_time": row.last_error_time or 0,
                }
        print(f"[health] restored {len(_channel_health)} health records from DB")
    except Exception as e:
        print(f"[health] failed to restore from DB: {e}")


async def _persist_health_keys(keys: set[str]):
    """Write health state to SQLite for the given keys."""
    if not keys:
        return
    try:
        async with SessionLocal() as session:
            for key in keys:
                health = _channel_health.get(key)
                if not health:
                    continue
                stmt = sqlite_upsert(HealthSnapshot).values(
                    health_key=key,
                    consecutive_failures=health["consecutive_failures"],
                    cooldown_until=health["cooldown_until"],
                    soft_cooldown_until=health.get("soft_cooldown_until", 0),
                    last_error=health.get("last_error", "")[:256],
                    total_requests=health.get("total_requests", 0),
                    failed_requests=health.get("failed_requests", 0),
                    last_success_time=health.get("last_success_time", 0),
                    last_error_time=health.get("last_error_time", 0),
                ).on_conflict_do_update(
                    index_elements=["health_key"],
                    set_={
                        "consecutive_failures": health["consecutive_failures"],
                        "cooldown_until": health["cooldown_until"],
                        "soft_cooldown_until": health.get("soft_cooldown_until", 0),
                        "last_error": health.get("last_error", "")[:256],
                        "total_requests": health.get("total_requests", 0),
                        "failed_requests": health.get("failed_requests", 0),
                        "last_success_time": health.get("last_success_time", 0),
                        "last_error_time": health.get("last_error_time", 0),
                    }
                )
                await session.execute(stmt)
            await session.commit()
    except Exception as e:
        print(f"[health] persist error: {e}")


async def _health_sync_loop():
    """后台任务：定期将健康状态持久化到 SQLite。"""
    global _dirty_keys
    while True:
        try:
            await asyncio.sleep(HEALTH_SYNC_INTERVAL)
            if _dirty_keys:
                keys = _dirty_keys.copy()
                _dirty_keys.clear()
                await _persist_health_keys(keys)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[health_sync] error: {e}")


async def final_sync_health():
    """关闭前最终同步所有健康状态。"""
    global _dirty_keys
    if _dirty_keys:
        keys = _dirty_keys.copy()
        _dirty_keys.clear()
        await _persist_health_keys(keys)


def _get_health(channel_id: int | str, upstream_model: str | None = None) -> dict:
    """获取或初始化渠道健康状态。"""
    key = health_key(channel_id, upstream_model) if isinstance(channel_id, int) else channel_id
    if key not in _channel_health:
        _channel_health[key] = {
            "consecutive_failures": 0,
            "cooldown_until": 0,
            "soft_cooldown_until": 0,
            "last_error": "",
            "total_requests": 0,
            "failed_requests": 0,
            "last_success_time": 0,
            "last_error_time": 0,
        }
    return _channel_health[key]


def is_circuit_open(channel_id: int | str, upstream_model: str | None = None) -> bool:
    """检查熔断器是否打开。"""
    return time.time() < _get_health(channel_id, upstream_model).get("cooldown_until", 0)


def is_soft_cooldown_open(channel_id: int | str, upstream_model: str | None = None) -> bool:
    """检查临时软冷却是否打开。"""
    return time.time() < _get_health(channel_id, upstream_model).get("soft_cooldown_until", 0)


def clear_circuit(channel_id: int | str, upstream_model: str | None = None):
    """清除熔断状态。"""
    health = _get_health(channel_id, upstream_model)
    health["cooldown_until"] = 0


def record_success(channel_id: int | str, upstream_model: str | None = None):
    """记录成功请求。"""
    health = _get_health(channel_id, upstream_model)
    health["consecutive_failures"] = 0
    health["cooldown_until"] = 0
    health["soft_cooldown_until"] = 0
    health["last_error"] = ""
    health["total_requests"] += 1
    health["last_success_time"] = time.time()
    _mark_dirty(channel_id, upstream_model)


def record_failure(channel_id: int | str, error: str, upstream_model: str | None = None) -> bool:
    """记录失败请求。返回是否达到自动禁用阈值。"""
    health = _get_health(channel_id, upstream_model)
    health["consecutive_failures"] += 1
    health["last_error"] = error[:200]
    health["total_requests"] += 1
    health["failed_requests"] += 1
    health["last_error_time"] = time.time()
    
    # 熔断逻辑
    if health["consecutive_failures"] >= CIRCUIT_FAILURE_THRESHOLD:
        cooldown = min(
            CIRCUIT_BASE_COOLDOWN * (2 ** (health["consecutive_failures"] - CIRCUIT_FAILURE_THRESHOLD)),
            CIRCUIT_MAX_COOLDOWN,
        )
        health["cooldown_until"] = time.time() + cooldown
    
    _mark_dirty(channel_id, upstream_model)
    return health["consecutive_failures"] >= AUTO_DISABLE_THRESHOLD


def record_soft_failure(channel_id: int | str, error: str, upstream_model: str | None = None, cooldown_seconds: float = 30.0) -> None:
    """Record a failed attempt without opening circuit, used for retryable heavy timeouts."""
    health = _get_health(channel_id, upstream_model)
    health["last_error"] = error[:200]
    health["total_requests"] += 1
    health["failed_requests"] += 1
    health["last_error_time"] = time.time()
    health["soft_cooldown_until"] = time.time() + max(float(cooldown_seconds), 0.0)
    _mark_dirty(channel_id, upstream_model)


def _mark_dirty(channel_id: int | str, upstream_model: str | None = None):
    """Mark a health key as dirty for periodic persistence."""
    global _dirty_keys
    key = health_key(channel_id, upstream_model) if isinstance(channel_id, int) else channel_id
    _dirty_keys.add(key)


def get_health_status(channel_id: int) -> dict:
    """获取渠道健康状态详情。"""
    prefix = f"{channel_id}:"
    related = [data for key, data in _channel_health.items() if key == str(channel_id) or key.startswith(prefix)]
    if related:
        total = sum(item["total_requests"] for item in related)
        failed = sum(item["failed_requests"] for item in related)
        consecutive_failures = max(item["consecutive_failures"] for item in related)
        cooldown_until = max(item["cooldown_until"] for item in related)
        soft_cooldown_until = max(item.get("soft_cooldown_until", 0) for item in related)
        last_success_time = max(item["last_success_time"] for item in related)
        last_error = next((item["last_error"] for item in sorted(related, key=lambda x: x.get("last_error_time", 0), reverse=True) if item["last_error"]), "")
        circuit_open = all(time.time() < item.get("cooldown_until", 0) for item in related)
    else:
        health = _get_health(channel_id)
        total = health["total_requests"]
        failed = health["failed_requests"]
        consecutive_failures = health["consecutive_failures"]
        cooldown_until = health["cooldown_until"]
        soft_cooldown_until = health.get("soft_cooldown_until", 0)
        last_error = health["last_error"]
        last_success_time = health["last_success_time"]
        circuit_open = time.time() < cooldown_until
    success_rate = ((total - failed) / total * 100) if total > 0 else 100
    
    return {
        "channel_id": channel_id,
        "consecutive_failures": consecutive_failures,
        "cooldown_until": cooldown_until,
        "soft_cooldown_until": soft_cooldown_until,
        "is_circuit_open": circuit_open,
        "is_soft_cooldown_open": time.time() < soft_cooldown_until,
        "total_requests": total,
        "failed_requests": failed,
        "success_rate": round(success_rate, 2),
        "last_error": last_error,
        "last_success_time": last_success_time,
        "should_auto_disable": consecutive_failures >= AUTO_DISABLE_THRESHOLD,
    }


async def start_health_checker(db_factory, channel_ids_func):
    """启动后台健康检查任务。"""
    while True:
        try:
            await asyncio.sleep(AUTO_RECOVERY_INTERVAL)
            channel_ids = await channel_ids_func()
            valid_prefixes = {f"{channel_id}:" for channel_id in channel_ids}
            valid_keys = {str(channel_id) for channel_id in channel_ids}
            for key, health in list(_channel_health.items()):
                if key not in valid_keys and not any(key.startswith(prefix) for prefix in valid_prefixes):
                    continue
                if health["consecutive_failures"] >= AUTO_DISABLE_THRESHOLD and time.time() > health.get("cooldown_until", 0):
                    health["consecutive_failures"] = CIRCUIT_FAILURE_THRESHOLD - 1
                    health["cooldown_until"] = 0
                    _mark_dirty(key, None)
                    print(f"[health_checker] {key} auto-recovery triggered")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[health_checker] error: {e}")


def reset_health(channel_id: int):
    """重置指定渠道的健康状态（手动恢复时使用）。"""
    prefix = f"{channel_id}:"
    keys = [key for key in _channel_health if key == str(channel_id) or key.startswith(prefix)]
    for key in keys or [str(channel_id)]:
        _channel_health[key] = {
            "consecutive_failures": 0,
            "cooldown_until": 0,
            "soft_cooldown_until": 0,
            "last_error": "",
            "total_requests": 0,
            "failed_requests": 0,
            "last_success_time": time.time(),
            "last_error_time": 0,
        }
        _mark_dirty(key, None)
