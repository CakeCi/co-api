import asyncio
import json
import time
from datetime import datetime
from sqlalchemy import insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.database import SessionLocal
from app.models import (
    RequestLog, StatsChannel, StatsDaily, StatsHourly,
    StatsModel, StatsToken,
)

_log_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=10000)
_log_consumer_task: asyncio.Task | None = None
_log_columns = set(RequestLog.__table__.columns.keys())


def _prepare_log(item: dict) -> dict:
    attempts = item.pop("_attempts", None)
    if attempts:
        item.setdefault("attempts_json", json.dumps(attempts, ensure_ascii=False))
        item.setdefault("retry_count", sum(1 for attempt in attempts if not attempt.get("ok")))
        channel_keys = {attempt.get("channel_id") or attempt.get("channel") for attempt in attempts}
        item.setdefault("fallback_used", 1 if len(channel_keys) > 1 else 0)
        last_attempt = attempts[-1]
        if not item.get("channel_id"):
            item["channel_id"] = last_attempt.get("channel_id")
        if not item.get("channel_name"):
            item["channel_name"] = last_attempt.get("channel")
        if not item.get("upstream_model"):
            item["upstream_model"] = last_attempt.get("upstream_model")
        if item.get("status") != 1 and not item.get("error_type"):
            failed_attempt = next((attempt for attempt in reversed(attempts) if not attempt.get("ok")), None)
            if failed_attempt:
                item["error_type"] = failed_attempt.get("error_type")
    return {key: value for key, value in item.items() if key in _log_columns}


def _parse_completed_at(item: dict) -> datetime:
    completed_at = item.get("completed_at")
    if isinstance(completed_at, datetime):
        return completed_at
    if isinstance(completed_at, str):
        try:
            return datetime.fromisoformat(completed_at)
        except ValueError:
            pass
    return datetime.now()


async def _upsert_stats(session, model, index_col, index_val, data: dict):
    """SQLite atomic upsert using INSERT ... ON CONFLICT DO UPDATE."""
    from sqlalchemy import text
    table_name = model.__tablename__
    columns = list(data.keys())
    # Include index column in INSERT
    all_columns = [index_col] + columns
    col_str = ", ".join(all_columns)
    placeholders = ", ".join([f":{c}" for c in all_columns])
    set_str = ", ".join([
        f"{c} = excluded.{c}"
        if c not in ("request_count", "success_count", "fail_count", "input_tokens", "output_tokens")
        else f"{c} = {table_name}.{c} + excluded.{c}"
        for c in columns if c != index_col
    ])
    # For avg_first_token_ms, use a CASE-based formula
    if "avg_first_token_ms" in columns:
        set_str = set_str.replace(
            f"avg_first_token_ms = {table_name}.avg_first_token_ms + excluded.avg_first_token_ms",
            f"avg_first_token_ms = CASE WHEN {table_name}.request_count > 0 THEN ({table_name}.avg_first_token_ms * ({table_name}.request_count - 1) + excluded.avg_first_token_ms) / {table_name}.request_count ELSE excluded.avg_first_token_ms END"
        )
    sql = text(f"""
        INSERT INTO {table_name} ({col_str})
        VALUES ({placeholders})
        ON CONFLICT ({index_col}) DO UPDATE SET {set_str}
    """)
    params = {**{index_col: index_val}, **data}
    await session.execute(sql, params)


async def _update_statistics(session, item: dict):
    """根据日志条目更新各维度统计表。"""
    status = item.get("status", 1)
    success = 1 if status == 1 else 0
    fail = 0 if status == 1 else 1
    prompt_tokens = item.get("prompt_tokens", 0) or 0
    completion_tokens = item.get("completion_tokens", 0) or 0
    first_token_ms = item.get("first_token_ms", 0) or 0
    model_name = item.get("model", "") or ""
    channel_id = item.get("channel_id")
    token_id = item.get("token_id")

    now = _parse_completed_at(item)
    hour_str = now.strftime("%Y-%m-%d_%H")
    date_str = now.strftime("%Y-%m-%d")

    # Hourly stats
    await _upsert_stats(session, StatsHourly, "hour", hour_str, {
        "request_count": 1, "success_count": success, "fail_count": fail,
        "input_tokens": prompt_tokens, "output_tokens": completion_tokens,
    })

    # Daily stats
    await _upsert_stats(session, StatsDaily, "date", date_str, {
        "request_count": 1, "success_count": success, "fail_count": fail,
        "input_tokens": prompt_tokens, "output_tokens": completion_tokens,
    })

    # Model stats
    if model_name:
        await _upsert_stats(session, StatsModel, "model_name", model_name, {
            "request_count": 1, "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
        })

    # Channel stats
    if channel_id:
        await _upsert_stats(session, StatsChannel, "channel_id", channel_id, {
            "request_count": 1, "success_count": success, "fail_count": fail,
            "input_tokens": prompt_tokens, "output_tokens": completion_tokens,
            "avg_first_token_ms": first_token_ms,
        })

    # Token stats
    if token_id:
        await _upsert_stats(session, StatsToken, "token_id", token_id, {
            "request_count": 1, "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
        })


async def log_consumer():
    """后台日志消费者：批量写入数据库。"""
    while True:
        batch = []
        try:
            item = await asyncio.wait_for(_log_queue.get(), timeout=1.0)
            batch.append(item)
            deadline = time.time() + 0.5
            while len(batch) < 50 and time.time() < deadline:
                try:
                    item = await asyncio.wait_for(_log_queue.get(), timeout=0.05)
                    batch.append(item)
                except asyncio.TimeoutError:
                    break
            if batch:
                await _flush_logs(batch)
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(f"[log_consumer] error: {e}")
            await asyncio.sleep(1)


async def _flush_logs(batch: list[dict]):
    """批量写入日志到数据库，并更新统计。"""
    prepared = [_prepare_log(item.copy()) for item in batch]
    if not prepared:
        return
    try:
        async with SessionLocal() as session:
            keys = set().union(*(item.keys() for item in prepared)) if prepared else set()
            normalized = [{key: item.get(key) for key in keys} for item in prepared]
            await session.execute(insert(RequestLog), normalized)
            # Update statistics
            for raw_item in batch:
                try:
                    await _update_statistics(session, raw_item)
                except Exception as e:
                    print(f"[_flush_logs] stats update error: {e}")
            await session.commit()
    except Exception as e:
        print(f"[_flush_logs] error writing {len(batch)} logs: {e}")
        await _flush_logs_one_by_one(batch)


async def _flush_logs_one_by_one(items: list[dict]):
    """Best-effort fallback so one malformed log does not drop the whole batch."""
    for item in items:
        try:
            async with SessionLocal() as session:
                prepared = _prepare_log(item.copy())
                await session.execute(insert(RequestLog), [prepared])
                try:
                    await _update_statistics(session, item)
                except Exception:
                    pass
                await session.commit()
        except Exception as e:
            print(f"[_flush_logs] dropped malformed log: {e}")


def enqueue_log(**kwargs) -> None:
    """将日志放入异步队列，不阻塞调用者。"""
    kwargs.setdefault("completed_at", datetime.now())
    try:
        _log_queue.put_nowait(kwargs)
    except asyncio.QueueFull:
        try:
            _log_queue.get_nowait()
            _log_queue.put_nowait(kwargs)
        except (asyncio.QueueEmpty, asyncio.QueueFull):
            pass


async def shutdown_log_writer():
    """关闭日志写入器，确保队列中的日志被写入。"""
    global _log_consumer_task
    if _log_consumer_task and not _log_consumer_task.done():
        _log_consumer_task.cancel()
        try:
            await _log_consumer_task
        except asyncio.CancelledError:
            pass
    remaining = []
    while not _log_queue.empty():
        try:
            remaining.append(_log_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    if remaining:
        await _flush_logs(remaining)


def start_log_consumer():
    """启动日志消费者后台任务。"""
    global _log_consumer_task
    if _log_consumer_task is None or _log_consumer_task.done():
        _log_consumer_task = asyncio.create_task(log_consumer())
