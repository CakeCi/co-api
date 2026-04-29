import asyncio
import base64
try:
    import orjson as json
except ImportError:
    import json
import random
import time
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.core.http_pool import get_http_client
from app.core.cache import (
    get_token_by_key,
    get_all_channels,
    get_all_pools,
    get_pool_members,
    invalidate_token,
    invalidate_channels,
    invalidate_pools,
    invalidate_all,
)
from app.core.log_writer import enqueue_log
from app.config import settings, reload_settings
from app.database import get_db
from app.models import (
    Channel, ModelPool, PoolMember, RequestLog,
    StatsChannel, StatsDaily, StatsHourly, StatsModel, StatsToken,
    Token, User,
)
from app.relay.converter import (
    AnthropicSSEToOpenAIConverter,
    anthropic_to_openai_request,
    anthropic_to_openai_response,
    bedrock_to_openai_request,
    gemini_to_openai_request,
    openai_sse_to_anthropic_sse,
    openai_to_anthropic_request,
    openai_to_anthropic_response,
    openai_to_bedrock_response,
    openai_to_gemini_response,
)

router = APIRouter()

from app.core.health import (
    is_circuit_open,
    is_soft_cooldown_open,
    clear_circuit,
    record_success as record_health_success,
    record_failure as record_health_failure,
    record_soft_failure as record_health_soft_failure,
    get_health_status,
    reset_health,
    start_health_checker,
    AUTO_DISABLE_THRESHOLD,
)

LOG_WRITE_COUNT = 0

XFYUN_RETRYABLE_CODES = {500, 10007, 10013, 10014, 10019, 10907, 10911}

# Load balancing: round-robin counters per model pool
_round_robin_counters: dict[int, int] = {}

# Session sticky: (token_id, model) -> (channel_id, timestamp)
_sticky_sessions: dict[tuple[int, str], tuple[int, float]] = {}
_sticky_ttl_seconds = 300  # 5 minutes


def parse_delay_config(value: str, fallback: list[float]) -> list[float]:
    try:
        delays = [float(item.strip()) for item in value.split(",") if item.strip()]
        return delays or fallback
    except Exception:
        return fallback


def primary_retry_delays() -> list[float]:
    return parse_delay_config(settings.primary_retry_delays, [2.0, 3.0, 4.0, 5.0])


def backup_retry_delays() -> list[float]:
    return parse_delay_config(settings.backup_retry_delays, [2.0])


def build_attempt_summary(attempts: list[dict]) -> str | None:
    if not attempts:
        return None
    parts = []
    for attempt in attempts:
        status_text = "ok" if attempt.get("ok") else "fail"
        error = attempt.get("error") or ""
        if error:
            parts.append(f"{attempt['channel']}:{status_text} {error[:80]}")
        else:
            parts.append(f"{attempt['channel']}:{status_text}")
    return " -> ".join(parts)


def classify_error(error) -> str | None:
    if not error:
        return None
    if isinstance(error, httpx.ReadTimeout):
        return "read_timeout"
    if isinstance(error, httpx.ConnectTimeout):
        return "connect_timeout"
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    if isinstance(error, httpx.HTTPStatusError):
        return f"http_{error.response.status_code}"
    text = str(error)
    if text == "circuit_open":
        return "circuit_open"
    if text == "soft_cooldown":
        return "soft_cooldown"
    if isinstance(error, PromptTooLargeForChannel):
        return "prompt_too_large"
    if "prompt_too_large_for_xunfei" in text:
        return "prompt_too_large"
    if "ReadTimeout" in text:
        return "read_timeout"
    if "stream_error" in text:
        return "stream_error"
    # Xfyun SSE errors
    if "SSE error:" in text:
        if "code: 10012" in text:
            return "xfyun_10012"
        if "code: 10010" in text or "code: 10110" in text or "code: 10222" in text:
            return "xfyun_temporary"
        if "code: 10907" in text or "code: 10910" in text:
            return "xfyun_context_overflow"
        if any(f"code: {c}" in text for c in ("10003", "10004", "10005", "10163", "10404")):
            return "xfyun_bad_request"
        if any(f"code: {c}" in text for c in ("10013", "10014", "10019")):
            return "xfyun_sensitive"
        return "xfyun_error"
    if "讯飞" in text:
        return "xfyun_error"
    return "upstream_error"


def parse_sse_error_from_chunk(chunk: str) -> tuple[str, str | None] | None:
    """Parse SSE error from chunk text. Returns (error_message, error_code_or_type) or None."""
    if not chunk or not chunk.startswith("data: "):
        return None
    try:
        data_str = chunk[6:].strip()
        if not data_str or data_str == "[DONE]":
            return None
        event_data = json.loads(data_str)
        # Drop upstream ping/heartbeat events silently
        if event_data.get("type") == "ping":
            return None
        # Anthropic SSE error format: {"type": "error", "error": {"message": "...", "type": "api_error"}}
        if event_data.get("type") == "error":
            error = event_data.get("error", {})
            msg = error.get("message", "")
            err_type = error.get("type", "")
            # Extract numeric code from message like "code: 10012"
            code = None
            if msg and "code:" in msg:
                parts = msg.split("code:")
                if len(parts) > 1:
                    code_candidate = parts[1].split(",")[0].strip()
                    if code_candidate.isdigit():
                        code = code_candidate
            return (msg, code or err_type)
        # OpenAI SSE error format: {"error": {"message": "...", "code": "...", "type": "..."}}
        if "error" in event_data:
            error = event_data.get("error", {})
            msg = error.get("message", "")
            code = error.get("code", "")
            return (msg, str(code) if code else error.get("type"))
    except Exception:
        return None
    return None


def is_xfyun_error_retryable(error_msg: str) -> bool:
    """Determine if a xfyun SSE error should trigger retry/fallback."""
    if not error_msg:
        return True
    # Context overflow: do not retry same channel
    if "code: 10907" in error_msg or "code: 10910" in error_msg:
        return False
    # Bad request / parameter errors: do not retry
    if any(f"code: {c}" in error_msg for c in ("10003", "10004", "10005", "10163", "10404")):
        return False
    # Sensitive content: do not retry, do not fallback
    if any(f"code: {c}" in error_msg for c in ("10013", "10014", "10019")):
        return False
    # Engine busy / temporary errors: retryable
    if any(f"code: {c}" in error_msg for c in ("10012", "10010", "10110", "10222")):
        return True
    return True


class PromptTooLargeForChannel(Exception):
    pass


class UnsupportedInputError(Exception):
    """Raised when the request requires capabilities no pool member supports."""
    pass


def _request_requires_vision(body: dict, api_format: str) -> bool:
    """Detect whether the request contains image/vision content."""
    if api_format == "openai":
        for msg in body.get("messages", []):
            content = msg.get("content") if isinstance(msg, dict) else None
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "image_url":
                        return True
            if isinstance(content, str) and content.strip().lower().startswith("data:image"):
                return True
    elif api_format == "anthropic":
        for msg in body.get("messages", []):
            content = msg.get("content") if isinstance(msg, dict) else None
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "image":
                        return True
    return False


def _channel_supports_vision(ch: Channel, upstream_model: str | None) -> bool:
    """Heuristic: infer whether a channel/model supports vision."""
    model_name = (upstream_model or ch.models or "").lower()
    channel_name = (ch.name or "").lower()
    # JMR channel supports vision models like gpt-image-2, mimo-v2-omni, etc.
    if "jmrai.net" in (ch.base_url or ""):
        return True
    # Known vision keywords
    vision_indicators = ("vision", "omni", "gpt-4o", "claude-3", "gemini", "gpt-4-turbo", "gpt-image")
    if any(ind in model_name for ind in vision_indicators):
        return True
    if any(ind in channel_name for ind in vision_indicators):
        return True
    # Known non-vision models
    non_vision = ("astron-code", "glm-5.1", "deepseek", "qwen-coder", "llama")
    if any(nv in model_name for nv in non_vision):
        return False
    # Conservative default: treat Anthropic-compatible coding endpoints as text-only
    if ch.api_type == "anthropic" and ("xf-yun.com" in ch.base_url or "coding" in ch.base_url):
        return False
    return False


def build_attempt(ch: Channel, upstream_model: str | None, priority: int, try_idx: int, ok: bool, error=None) -> dict:
    attempt = {
        "channel_id": ch.id,
        "channel": ch.name,
        "upstream_model": upstream_model,
        "priority": priority,
        "try": try_idx + 1,
        "ok": ok,
    }
    if error:
        attempt["error"] = str(error)[:500]
        attempt["error_type"] = classify_error(error)
    return attempt


def _json_dumps(obj, **kwargs) -> str:
    result = json.dumps(obj, **kwargs)
    if isinstance(result, bytes):
        result = result.decode('utf-8')
    return result

def build_attempt_observability(attempts: list[dict]) -> dict:
    if not attempts:
        return {"attempts_json": None, "retry_count": 0, "fallback_used": 0}
    channel_keys = {attempt.get("channel_id") or attempt.get("channel") for attempt in attempts}
    retry_count = sum(1 for attempt in attempts if not attempt.get("ok"))
    return {
        "attempts_json": _json_dumps(attempts, ensure_ascii=False),
        "retry_count": retry_count,
        "fallback_used": 1 if len(channel_keys) > 1 else 0,
    }


def final_request_filter():
    # 兼容旧日志：以前 fallback 候选失败会独立写入 [候选...] 失败日志。
    return or_(RequestLog.error_msg.is_(None), ~RequestLog.error_msg.like("[候选%"))


def _estimate_text_tokens(text: str) -> int:
    """Estimate tokens without a tokenizer, accounting for CJK vs ASCII-heavy text."""
    if not text:
        return 0
    cjk_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    other_chars = len(text) - cjk_chars
    return int(cjk_chars / 1.5) + int(other_chars / 4.0)


def estimate_prompt_tokens(body: dict) -> int:
    """粗略估算 prompt tokens。按中文和 ASCII/JSON/代码分别估算，避免英文上下文严重高估。"""
    messages = body.get("messages", [])
    estimated = 0
    if isinstance(body.get("system"), str):
        estimated += _estimate_text_tokens(body["system"])
    for msg in messages:
        content = msg.get("content", "") if isinstance(msg, dict) else ""
        if isinstance(content, str):
            estimated += _estimate_text_tokens(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    estimated += _estimate_text_tokens(block.get("text", ""))
    base = max(1, estimated)
    overhead = len(messages) * 4 + 10
    return base + overhead


def extract_message_text(msg: dict, max_chars: int = 1200) -> str:
    content = msg.get("content", "")
    parts = []
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif block.get("type") in ("image_url", "image"):
                    parts.append(f"[{block.get('type')}]")
            elif isinstance(block, str):
                parts.append(block)
    elif content:
        parts.append(str(content))
    text = "\n".join(part for part in parts if part).strip()
    return text[:max_chars]


def compact_chat_messages(body: dict, original_estimated_tokens: int) -> tuple[dict, dict] | None:
    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) <= 3:
        return None

    preserve_recent = max(int(settings.compact_preserve_recent_messages), 2)
    summary_max_chars = max(int(settings.compact_summary_max_chars), 1000)
    target_tokens = max(int(settings.auto_compact_target_tokens), 1000)

    best_body = None
    best_estimated = original_estimated_tokens
    while preserve_recent >= 2:
        recent_start = max(len(messages) - preserve_recent, 0)
        while recent_start > 0 and messages[recent_start].get("role") == "tool":
            recent_start -= 1

        leading = [msg for msg in messages[:recent_start] if msg.get("role") in ("system", "developer")]
        compacted = [msg for msg in messages[:recent_start] if msg.get("role") not in ("system", "developer")]
        recent = messages[recent_start:]
        if not compacted:
            return None

        summary_lines = [
            "[co-api context compaction] Older conversation history was compacted to stay within the target context window.",
            "Preserve these facts and decisions when answering:",
        ]
        used_chars = sum(len(line) for line in summary_lines)
        for index, msg in enumerate(compacted, 1):
            role = msg.get("role", "user")
            text = extract_message_text(msg)
            if not text and msg.get("tool_calls"):
                text = f"tool_calls={len(msg.get('tool_calls') or [])}"
            line = f"{index}. {role}: {text}"
            if used_chars + len(line) > summary_max_chars:
                summary_lines.append(f"... {len(compacted) - index + 1} older messages omitted from compacted summary.")
                break
            summary_lines.append(line)
            used_chars += len(line)

        summary_msg = {"role": "system", "content": "\n".join(summary_lines)}
        candidate_body = body.copy()
        candidate_body["messages"] = leading + [summary_msg] + recent
        candidate_estimated = estimate_prompt_tokens(candidate_body)
        best_body = candidate_body
        best_estimated = candidate_estimated
        if candidate_estimated <= target_tokens:
            break
        preserve_recent -= 2

    if not best_body or best_estimated >= original_estimated_tokens:
        return None
    return best_body, {
        "action": "auto_compact",
        "original_estimated_prompt_tokens": original_estimated_tokens,
        "compacted_estimated_prompt_tokens": best_estimated,
    }


def maybe_compact_context(body: dict, api_format: str, estimated_prompt_tokens: int) -> tuple[dict, dict]:
    policy = (settings.context_overflow_policy or "route_only").lower()
    info = {
        "action": "none",
        "original_estimated_prompt_tokens": estimated_prompt_tokens,
        "compacted_estimated_prompt_tokens": estimated_prompt_tokens,
    }
    if policy == "reject" and estimated_prompt_tokens > settings.auto_compact_trigger_tokens:
        raise HTTPException(status_code=400, detail=f"上下文超过配置阈值: {estimated_prompt_tokens}")
    if api_format != "openai":
        return body, info
    if policy != "auto_compact" and not settings.auto_compact_enabled:
        return body, info
    if estimated_prompt_tokens <= settings.auto_compact_trigger_tokens:
        return body, info
    compacted = compact_chat_messages(body, estimated_prompt_tokens)
    if not compacted:
        info["action"] = "compact_skipped"
        return body, info
    return compacted


def raise_for_xfyun_error(resp_data: dict):
    """检查讯飞非标准错误码，根据分类抛出异常。"""
    code = resp_data.get("code")
    if code is None or code == 0:
        return
    message = resp_data.get("message") or resp_data.get("desc") or f"讯飞错误码 {code}"
    if code in XFYUN_RETRYABLE_CODES:
        raise httpx.HTTPError(f"讯飞可重试错误 {code}: {message}")
    raise HTTPException(status_code=400, detail=f"讯飞错误 {code}: {message}")


def parse_json_or_xfyun_data(raw_body: bytes) -> dict:
    text = raw_body.decode("utf-8", errors="replace").strip()
    if text.startswith("data:"):
        text = text[5:].strip()
    return json.loads(text)


async def cleanup_old_logs(db: AsyncSession):
    """清理超过500条的旧日志 body 字段，保留统计字段。"""
    result = await db.execute(select(func.count(RequestLog.id)))
    total = result.scalar() or 0
    retention_count = max(settings.log_body_retention_count, 1)
    if total <= retention_count:
        return
    keep_result = await db.execute(select(RequestLog.id).order_by(RequestLog.id.desc()).limit(retention_count))
    keep_ids = [row[0] for row in keep_result.all()]
    if keep_ids:
        old_result = await db.execute(select(RequestLog).where(~RequestLog.id.in_(keep_ids)))
        for log in old_result.scalars().all():
            log.request_body = None
            log.response_body = None
        await db.commit()


def get_http_timeout(estimated_prompt_tokens: int) -> httpx.Timeout:
    read_timeout = settings.read_timeout_heavy if estimated_prompt_tokens >= settings.retry_prompt_threshold else settings.read_timeout_light
    return httpx.Timeout(
        connect=settings.connect_timeout,
        read=read_timeout,
        write=settings.write_timeout,
        pool=settings.pool_timeout,
    )


def should_count_failure(exc: Exception, estimated_prompt_tokens: int) -> bool:
    return not (isinstance(exc, httpx.ReadTimeout) and estimated_prompt_tokens >= settings.retry_prompt_threshold)


def is_xunfei_channel(ch: Channel) -> bool:
    return ch.api_type == "anthropic" and ("xf-yun.com" in ch.base_url or "xunfei" in ch.name.lower())


def extract_usage(data: dict) -> tuple[int, int, int]:
    usage = data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}
    prompt_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0
    total_tokens = usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens)
    return int(prompt_tokens or 0), int(completion_tokens or 0), int(total_tokens or 0)


def estimate_completion_tokens_from_response(data: dict) -> int:
    estimated_text = []
    for choice in data.get("choices", []) or []:
        message = choice.get("message", {}) if isinstance(choice, dict) else {}
        content = message.get("content")
        if isinstance(content, str):
            estimated_text.append(content)
    return _estimate_text_tokens("".join(estimated_text))


async def write_log(db: AsyncSession, **kwargs) -> RequestLog:
    global LOG_WRITE_COUNT
    attempts = kwargs.pop("_attempts", None)
    if attempts:
        kwargs.update({key: value for key, value in build_attempt_observability(attempts).items() if kwargs.get(key) is None})
        last_attempt = attempts[-1]
        kwargs.setdefault("channel_name", last_attempt.get("channel"))
        kwargs.setdefault("upstream_model", last_attempt.get("upstream_model"))
        if not kwargs.get("error_type"):
            failed_attempt = next((attempt for attempt in reversed(attempts) if not attempt.get("ok")), None)
            if failed_attempt:
                kwargs["error_type"] = failed_attempt.get("error_type")
    log = RequestLog(**kwargs)
    db.add(log)
    await db.commit()
    LOG_WRITE_COUNT += 1
    cleanup_interval = max(settings.log_cleanup_interval, 1)
    if LOG_WRITE_COUNT % cleanup_interval == 0:
        await cleanup_old_logs(db)
    return log


def require_admin(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_token(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    return payload


def parse_models(value) -> str:
    if isinstance(value, list):
        return ",".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "")


def models_to_list(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def weighted_order(group: list[tuple[Channel, str, int]]) -> list[tuple[Channel, str, int]]:
    """Return candidates in weighted-random order without replacement."""
    remaining = list(group)
    ordered = []
    while remaining:
        total_weight = sum(max(weight, 1) for _, _, weight in remaining)
        pick = random.uniform(0, total_weight)
        current = 0.0
        for index, item in enumerate(remaining):
            current += max(item[2], 1)
            if pick <= current:
                ordered.append(item)
                remaining.pop(index)
                break
    return ordered


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def is_masked_secret(value: str | None) -> bool:
    return bool(value and ("*" in value or "..." in value))


@router.post("/api/login")
async def login(data: dict, db: AsyncSession = Depends(get_db)):
    username = data.get("username", "")
    password = data.get("password", "")
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.password_hash:
        raise HTTPException(status_code=503, detail="管理员密码未初始化，请在数据库中设置 password_hash")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token({"sub": user.username, "uid": user.id})
    return {"success": True, "token": token, "username": user.username, "data": {"token": token, "username": user.username}}


@router.get("/api/me")
async def me(request: Request):
    payload = require_admin(request)
    return {"success": True, "data": payload}


@router.get("/api/channels")
async def list_channels(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    require_admin(request)
    # Get total count
    count_result = await db.execute(select(func.count()).select_from(Channel))
    total = count_result.scalar()
    
    # Get paginated data
    offset = (page - 1) * limit
    result = await db.execute(
        select(Channel).order_by(Channel.id).offset(offset).limit(limit)
    )
    items = [serialize_channel(ch) for ch in result.scalars().all()]
    
    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    }


def serialize_channel(ch: Channel) -> dict:
    return {
        "id": ch.id,
        "name": ch.name,
        "base_url": ch.base_url,
        "api_key": mask_secret(ch.api_key),
        "has_api_key": bool(ch.api_key),
        "models": models_to_list(ch.models),
        "api_type": ch.api_type,
        "status": ch.status,
        "created_at": str(ch.created_at) if ch.created_at else None,
    }


@router.post("/api/channels")
async def create_channel(data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    ch = Channel(
        name=data.get("name", ""),
        base_url=(data.get("base_url") or "").rstrip("/"),
        api_key=data.get("api_key", ""),
        models=parse_models(data.get("models", "")),
        api_type=data.get("api_type", "openai"),
        status=data.get("status", 1),
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    invalidate_channels()
    return {"success": True, "message": "渠道创建成功", "id": ch.id}


@router.put("/api/channels/{channel_id}")
async def update_channel(channel_id: int, data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="渠道不存在")
    for field in ("name", "api_type", "status"):
        if field in data:
            setattr(ch, field, data[field])
    if "api_key" in data and data.get("api_key") and not is_masked_secret(data.get("api_key")):
        ch.api_key = data["api_key"]
    if "models" in data:
        ch.models = parse_models(data["models"])
    if "base_url" in data:
        ch.base_url = (data.get("base_url") or "").rstrip("/")
    await db.commit()
    invalidate_channels()
    return {"success": True, "message": "渠道更新成功"}


@router.delete("/api/channels/{channel_id}")
async def delete_channel(channel_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    await db.execute(delete(PoolMember).where(PoolMember.channel_id == channel_id))
    await db.execute(delete(Channel).where(Channel.id == channel_id))
    await db.commit()
    invalidate_channels()
    invalidate_pools()
    return {"success": True, "message": "渠道删除成功"}


@router.post("/api/channels/{channel_id}/test")
async def test_channel(channel_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="渠道不存在")
    try:
        model = (ch.models or "gpt-3.5-turbo").split(",")[0].strip()
        url, headers, upstream_body = build_upstream_request(
            ch,
            model,
            model,
            {"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 8},
            "openai",
        )
        timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)
        client = get_http_client()
        resp = await client.post(url, headers=headers, json=upstream_body, timeout=timeout)
        resp.raise_for_status()
        body = None
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:2000]
        models = []
        if isinstance(body, dict) and isinstance(body.get("data"), list):
            models = body.get("data", [])
        return {
            "success": True,
            "message": "连接成功",
            "status_code": resp.status_code,
            "request": {"method": "POST", "url": url, "headers": {"Authorization": "Bearer ***", "Content-Type": "application/json"}},
            "response": {"status_code": resp.status_code, "headers": dict(resp.headers), "body": body},
            "models": models,
        }
    except Exception as e:
        return {"success": False, "message": str(e)[:500], "status_code": 0, "response": {"status_code": 0, "body": str(e)[:1000]}}


@router.get("/api/channels/{channel_id}/health")
async def get_channel_health(channel_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="渠道不存在")
    health = get_health_status(ch.id)
    return {"success": True, "data": health}


@router.post("/api/channels/{channel_id}/reset-health")
async def reset_channel_health(channel_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="渠道不存在")
    reset_health(ch.id)
    # 如果渠道被自动禁用，重新启用
    if ch.status == 0:
        ch.status = 1
        await db.commit()
        invalidate_channels()
    return {"success": True, "message": "健康状态已重置"}


@router.get("/api/tokens")
async def list_tokens(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    require_admin(request)
    # Get total count
    count_result = await db.execute(select(func.count()).select_from(Token))
    total = count_result.scalar()
    
    # Get paginated data
    offset = (page - 1) * limit
    result = await db.execute(
        select(Token).order_by(Token.id).offset(offset).limit(limit)
    )
    items = []
    for token in result.scalars().all():
        items.append({
            "id": token.id,
            "name": token.name,
            "key": mask_secret(token.key),
            "status": token.status,
            "created_at": str(token.created_at) if token.created_at else None,
        })
    
    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    }


@router.post("/api/tokens")
async def create_token_api(data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    key = "sk-" + __import__("secrets").token_urlsafe(32)
    token = Token(name=data.get("name", "default"), key=key, status=1)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return {"success": True, "message": "令牌创建成功", "data": {"id": token.id, "key": key}}


@router.delete("/api/tokens/{token_id}")
async def delete_token_api(token_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(Token).where(Token.id == token_id))
    token = result.scalar_one_or_none()
    if token:
        invalidate_token(token.key)
    await db.execute(delete(Token).where(Token.id == token_id))
    await db.commit()
    return {"success": True, "message": "令牌删除成功"}


@router.get("/api/logs")
async def list_logs(
    request: Request,
    page: int = 1,
    limit: int = 20,
    token_id: int | None = None,
    model: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    require_admin(request)
    page = max(page, 1)
    limit = max(1, min(limit, 100))
    conds = [final_request_filter()]
    if token_id:
        conds.append(RequestLog.token_id == token_id)
    if model:
        conds.append(RequestLog.model == model)
    total_result = await db.execute(select(func.count(RequestLog.id)).where(*conds))
    total = total_result.scalar() or 0
    result = await db.execute(
        select(RequestLog).where(*conds).order_by(RequestLog.id.desc()).offset((page - 1) * limit).limit(limit)
    )
    logs = []
    for log in result.scalars().all():
        logs.append(serialize_log(log))
    pages = max(1, (total + limit - 1) // limit) if limit else 1
    return {"success": True, "data": {"items": logs, "logs": logs, "total": total, "page": page, "pages": pages, "limit": limit}}


def serialize_log(log: RequestLog) -> dict:
    attempts = None
    if log.attempts_json:
        try:
            attempts = json.loads(log.attempts_json)
        except json.JSONDecodeError:
            attempts = None
    return {
        "id": log.id,
        "token_id": log.token_id,
        "token_name": log.token_name,
        "channel_id": log.channel_id,
        "channel_name": log.channel_name,
        "model": log.model,
        "upstream_model": log.upstream_model,
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "total_tokens": log.total_tokens,
        "estimated_prompt_tokens": log.estimated_prompt_tokens,
        "estimated_completion_tokens": log.estimated_completion_tokens,
        "duration_ms": log.duration_ms,
        "first_token_ms": log.first_token_ms,
        "is_stream": log.is_stream,
        "status": log.status,
        "error_type": log.error_type,
        "retry_count": log.retry_count,
        "fallback_used": log.fallback_used,
        "attempts_json": log.attempts_json,
        "attempts": attempts,
        "error_msg": log.error_msg,
        "has_detail": bool(log.request_body or log.response_body),
        "created_at": str(log.created_at) if log.created_at else None,
    }


@router.get("/api/logs/{log_id}")
async def get_log_detail(log_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(RequestLog).where(RequestLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    data = serialize_log(log)
    data["request_body"] = log.request_body
    data["response_body"] = log.response_body
    return {"success": True, "data": data}


@router.get("/api/model-pools")
async def list_model_pools(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    require_admin(request)
    # Get total count
    count_result = await db.execute(select(func.count()).select_from(ModelPool))
    total = count_result.scalar()
    
    # Get paginated data
    offset = (page - 1) * limit
    result = await db.execute(
        select(ModelPool).order_by(ModelPool.id).offset(offset).limit(limit)
    )
    pools = []
    for pool in result.scalars().all():
        count_result = await db.execute(select(func.count(PoolMember.id)).where(PoolMember.pool_id == pool.id))
        pools.append({
            "id": pool.id,
            "name": pool.name,
            "description": pool.description,
            "status": pool.status,
            "member_count": count_result.scalar() or 0,
            "created_at": str(pool.created_at) if pool.created_at else None,
        })
    
    return {
        "success": True,
        "data": {
            "items": pools,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    }


@router.post("/api/model-pools")
async def create_model_pool(data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    pool = ModelPool(name=data.get("name", ""), description=data.get("description", ""), status=data.get("status", 1))
    db.add(pool)
    await db.commit()
    await db.refresh(pool)
    invalidate_pools()
    return {"success": True, "message": "模型池创建成功", "id": pool.id}


@router.put("/api/model-pools/{pool_id}")
async def update_model_pool(pool_id: int, data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(ModelPool).where(ModelPool.id == pool_id))
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail="模型池不存在")
    for field in ("name", "description", "status"):
        if field in data:
            setattr(pool, field, data[field])
    await db.commit()
    invalidate_pools()
    return {"success": True, "message": "模型池更新成功"}


@router.delete("/api/model-pools/{pool_id}")
async def delete_model_pool(pool_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    await db.execute(delete(PoolMember).where(PoolMember.pool_id == pool_id))
    await db.execute(delete(ModelPool).where(ModelPool.id == pool_id))
    await db.commit()
    invalidate_pools()
    return {"success": True, "message": "模型池删除成功"}


@router.get("/api/model-pools/{pool_id}/members")
async def list_pool_members(pool_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(
        select(PoolMember).where(PoolMember.pool_id == pool_id).order_by(PoolMember.priority, PoolMember.weight.desc())
    )
    data = []
    for member in result.scalars().all():
        channel_result = await db.execute(select(Channel).where(Channel.id == member.channel_id))
        channel = channel_result.scalar_one_or_none()
        data.append({
            "id": member.id,
            "pool_id": member.pool_id,
            "channel_id": member.channel_id,
            "channel_name": channel.name if channel else "未知",
            "alias": member.alias,
            "weight": member.weight,
            "priority": member.priority,
            "status": member.status,
        })
    return {"success": True, "data": data}


@router.post("/api/model-pools/{pool_id}/members")
async def add_pool_member(pool_id: int, data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    member = PoolMember(
        pool_id=pool_id,
        channel_id=data.get("channel_id"),
        alias=data.get("alias", ""),
        weight=data.get("weight", 100),
        priority=data.get("priority", 1),
        status=1,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    invalidate_pools()
    return {"success": True, "message": "成员添加成功", "id": member.id}


@router.put("/api/model-pools/{pool_id}/members/{member_id}")
async def update_pool_member(pool_id: int, member_id: int, data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(PoolMember).where(PoolMember.id == member_id, PoolMember.pool_id == pool_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    for field in ("channel_id", "alias", "weight", "priority", "status"):
        if field in data:
            setattr(member, field, data[field])
    await db.commit()
    invalidate_pools()
    return {"success": True, "message": "成员更新成功"}


@router.delete("/api/model-pools/{pool_id}/members/{member_id}")
async def delete_pool_member(pool_id: int, member_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    await db.execute(delete(PoolMember).where(PoolMember.id == member_id, PoolMember.pool_id == pool_id))
    await db.commit()
    invalidate_pools()
    return {"success": True, "message": "成员删除成功"}


async def get_pool_members_by_model(db: AsyncSession, model: str) -> list[tuple[Channel, str, int, int]]:
    """根据模型名查找模型池成员，返回 [(channel, alias, priority, weight), ...]。"""
    pools = await get_all_pools(db)
    pool = next((p for p in pools if p.name == model), None)
    if not pool:
        return []
    members = await get_pool_members(db, pool.id)
    channels = await get_all_channels(db)
    channel_map = {ch.id: ch for ch in channels}
    candidates = []
    for member in members:
        channel = channel_map.get(member.channel_id)
        if channel:
            candidates.append((channel, member.alias or model, member.priority or 1, member.weight or 100))
    return candidates


async def get_channel_by_model(db: AsyncSession, model: str) -> tuple[Channel | None, str | None]:
    channels = await get_all_channels(db)
    candidates = [ch for ch in channels if model in models_to_list(ch.models)]
    if not candidates:
        return None, None
    ch = random.choice(candidates)
    return ch, model


async def require_api_token(request: Request, db: AsyncSession = Depends(get_db)):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer sk-"):
        raise HTTPException(status_code=401, detail="无效的 API 密钥")
    token_obj = await get_token_by_key(db, auth[7:])
    if not token_obj:
        raise HTTPException(status_code=401, detail="无效的 API 密钥")
    return token_obj


def _detect_model_capabilities(model_name: str) -> dict:
    """Detect model capabilities for metadata signaling to clients (opencode, etc.)."""
    name_lower = model_name.lower()
    caps = {}
    if any(kw in name_lower for kw in ("o1", "o3", "o4", "deepseek-r1", "deepseek-reasoner",
        "kimi-k2", "gpt-5", "gemini-2.5-pro", "gemini-3", "claude-4", "sonnet-4", "haiku-4")):
        caps["supports_reasoning"] = True
    if any(kw in name_lower for kw in ("vision", "omni", "gpt-4o", "gpt-image",
        "claude-3", "gemini-3", "gemini-2.5", "kimi-k2", "mimo-v2-omni")):
        caps["supports_vision"] = True
    if "embedding" not in name_lower and "whisper" not in name_lower and "tts" not in name_lower:
        caps["supports_function_calling"] = True
    return caps


KNOWN_PLATFORMS = {
    "deepseek": {"base_url": "https://api.deepseek.com", "api_type": "openai", "models": "deepseek-chat,deepseek-reasoner"},
    "kimi": {"base_url": "https://api.moonshot.cn", "api_type": "openai", "models": "moonshot-v1-8k,moonshot-v1-32k,moonshot-v1-128k,kimi-k2"},
    "kimi-coding": {"base_url": "https://api.kimi.com/coding/v1", "api_type": "openai", "models": "kimi-for-coding"},
    "zhipu": {"base_url": "https://open.bigmodel.cn/api/paas/v4", "api_type": "openai", "models": "glm-4,glm-4-flash"},
    "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "api_type": "openai", "models": "qwen-plus,qwen-max,qwen-turbo"},
    "siliconflow": {"base_url": "https://api.siliconflow.cn", "api_type": "openai", "models": "deepseek-ai/DeepSeek-V3,deepseek-ai/DeepSeek-R1,Qwen/Qwen2.5-7B-Instruct"},
}


@router.get("/api/platforms")
async def list_platforms(request: Request):
    """Return known API platform presets for quick channel setup."""
    require_admin(request)
    return {"success": True, "data": KNOWN_PLATFORMS}


@router.get("/v1/models")
async def list_models(request: Request, db: AsyncSession = Depends(get_db), token: Token = Depends(require_api_token)):
    result = await db.execute(select(Channel).where(Channel.status == 1))
    all_models = set()
    for ch in result.scalars().all():
        all_models.update(m.strip() for m in (ch.models or "").split(",") if m.strip())
    pools_result = await db.execute(select(ModelPool).where(ModelPool.status == 1))
    for pool in pools_result.scalars().all():
        all_models.add(pool.name)
    data = []
    for m in sorted(all_models):
        caps = _detect_model_capabilities(m)
        entry = {"id": m, "object": "model", "created": 1677649963, "owned_by": "co-api"}
        if caps:
            entry["capabilities"] = caps
        data.append(entry)
    return {"object": "list", "data": data}


def build_upstream_request(ch: Channel, alias: str | None, model: str, body: dict, api_format: str):
    upstream_model = alias or model
    upstream_body = body.copy()
    if "model" in upstream_body:
        upstream_body["model"] = upstream_model
    if "modelId" in upstream_body:
        upstream_body["modelId"] = upstream_model

    # Reasoning effort passthrough for OpenAI→OpenAI
    reasoning_keys = ("reasoning_effort", "reasoning_summary")
    reasoning_fields = {}
    for key in reasoning_keys:
        if key in upstream_body:
            reasoning_fields[key] = upstream_body.pop(key)

    if api_format == "openai" and ch.api_type == "anthropic":
        upstream_body = openai_to_anthropic_request(upstream_body)
    elif api_format == "anthropic" and ch.api_type == "openai":
        upstream_body = anthropic_to_openai_request(upstream_body)
    elif api_format == "gemini" and ch.api_type == "openai":
        upstream_body = gemini_to_openai_request(upstream_body)
    elif api_format == "bedrock" and ch.api_type == "openai":
        upstream_body = bedrock_to_openai_request(upstream_body)

    # Restore reasoning fields for OpenAI→OpenAI paths
    if ch.api_type == "openai" and reasoning_fields:
        for key, val in reasoning_fields.items():
            upstream_body[key] = val

    # Normalize base URL: strip trailing /v1 if present, we append the right path
    base_url = (ch.base_url or "").rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3].rstrip("/")

    if ch.api_type == "anthropic":
        url = f"{base_url}/v1/messages"
    elif ch.api_type == "gemini":
        url = f"{base_url}/v1beta/models/{upstream_model}:generateContent"
    elif ch.api_type == "bedrock":
        url = f"{base_url}/model/{upstream_model}/converse"
    else:
        url = f"{base_url}/v1/chat/completions"

    headers = {"Authorization": f"Bearer {ch.api_key}", "Content-Type": "application/json"}
    # Parse and add custom headers from channel config
    if ch.custom_headers:
        try:
            custom = json.loads(ch.custom_headers)
            if isinstance(custom, dict):
                headers.update({k: str(v) for k, v in custom.items()})
        except Exception:
            pass
    return url, headers, upstream_body


def _apply_lb_strategy(
    candidates_by_priority: dict[int, list[tuple[Channel, str, int]]],
    mode: str,
    pool_id: int | None,
    token_id: int,
    model: str,
) -> dict[int, list[tuple[Channel, str, int]]]:
    """应用负载均衡策略，返回按优先级分组的候选列表。"""
    if not candidates_by_priority:
        return candidates_by_priority

    # Sticky session: check if we should pin to a previous channel
    if mode == "sticky" and token_id:
        sticky_key = (token_id, model)
        now = time.time()
        sticky_ch_id, sticky_ts = _sticky_sessions.get(sticky_key, (0, 0))
        if sticky_ch_id and (now - sticky_ts) < _sticky_ttl_seconds:
            # Find the sticky channel and move it to front of its priority group
            for priority, group in candidates_by_priority.items():
                for idx, (ch, alias, weight) in enumerate(group):
                    if ch.id == sticky_ch_id:
                        # Move to front
                        group.insert(0, group.pop(idx))
                        candidates_by_priority[priority] = group
                        return candidates_by_priority

    # Round Robin: rotate starting position per pool
    if mode == "round_robin" and pool_id is not None:
        counter = _round_robin_counters.get(pool_id, 0)
        _round_robin_counters[pool_id] = counter + 1
        # Flatten all candidates, rotate, then re-group by priority
        flat = []
        for priority in sorted(candidates_by_priority.keys()):
            flat.extend([(priority, item) for item in candidates_by_priority[priority]])
        if flat:
            n = len(flat)
            start = counter % n
            rotated = flat[start:] + flat[:start]
            new_groups: dict[int, list] = {}
            for priority, item in rotated:
                new_groups.setdefault(priority, []).append(item)
            return new_groups

    # Weighted mode: apply weighted_order to each priority group
    if mode == "weighted":
        for priority, group in candidates_by_priority.items():
            candidates_by_priority[priority] = weighted_order(group)
        return candidates_by_priority

    # Failover mode: already sorted by priority, keep as-is
    return candidates_by_priority


def _record_sticky(token_id: int, model: str, channel_id: int):
    """记录会话粘性映射。"""
    _sticky_sessions[(token_id, model)] = (channel_id, time.time())


def convert_response(data: dict, api_format: str, channel_type: str) -> dict:
    if api_format == "openai" and channel_type == "anthropic":
        return anthropic_to_openai_response(data)
    if api_format == "anthropic" and channel_type == "openai":
        return openai_to_anthropic_response(data)
    if api_format == "gemini" and channel_type == "openai":
        return openai_to_gemini_response(data)
    if api_format == "bedrock" and channel_type == "openai":
        return openai_to_bedrock_response(data)
    return data


def openai_chunk(payload: dict) -> str:
    result = json.dumps(payload, ensure_ascii=False)
    if isinstance(result, bytes):
        result = result.decode('utf-8')
    return f"data: {result}\n\n"


async def simulate_openai_stream(data: dict, usage: dict, delay: float = 0.02):
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content", "") or ""
    tool_calls = message.get("tool_calls", [])
    resp_id = data.get("id", "")
    resp_created = data.get("created", int(time.time()))
    resp_model = data.get("model", "")
    finish_reason = choice.get("finish_reason", "stop")

    yield openai_chunk({"id": resp_id, "object": "chat.completion.chunk", "created": resp_created, "model": resp_model, "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]})
    if content:
        for i in range(0, len(content), 4):
            yield openai_chunk({"id": resp_id, "object": "chat.completion.chunk", "created": resp_created, "model": resp_model, "choices": [{"index": 0, "delta": {"content": content[i:i + 4]}, "finish_reason": None}]})
            await asyncio.sleep(delay)
    for idx, tc in enumerate(tool_calls or []):
        yield openai_chunk({"id": resp_id, "object": "chat.completion.chunk", "created": resp_created, "model": resp_model, "choices": [{"index": 0, "delta": {"tool_calls": [{"index": idx, "id": tc.get("id", ""), "type": "function", "function": tc.get("function", {})}]}, "finish_reason": None}]})
    yield openai_chunk({"id": resp_id, "object": "chat.completion.chunk", "created": resp_created, "model": resp_model, "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}]})
    if usage:
        yield openai_chunk({"id": resp_id, "object": "chat.completion.chunk", "created": resp_created, "model": resp_model, "choices": [], "usage": usage})
    yield "data: [DONE]\n\n"


def convert_sse_event(event_text: str, api_format: str, channel_type: str, converter=None) -> str:
    # Filter upstream ping/heartbeat events before conversion
    if _is_ping_sse_event(event_text):
        return ""
    if api_format == "anthropic" and channel_type == "openai":
        return openai_sse_to_anthropic_sse(event_text)
    if converter:
        return converter.convert(event_text)
    return event_text


def _is_ping_sse_event(event_text: str) -> bool:
    """Check if SSE event text is an upstream ping/heartbeat that should be dropped.
    Handles both bare data: lines and events prefixed with event: ping."""
    if not event_text:
        return False
    ping_detected = False
    for line in event_text.strip().split("\n"):
        if line.startswith("event: ") and "ping" in line.lower():
            ping_detected = True
        if line.startswith("data: "):
            try:
                data_str = line[6:].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                event_data = json.loads(data_str)
                if event_data.get("type") == "ping":
                    return True
            except Exception:
                pass
    # Also match if event: ping hint was found but no data payload
    return ping_detected


def extract_usage_from_sse(chunk: str) -> tuple[int, int, int] | None:
    if '"usage"' not in chunk or not chunk.startswith("data: "):
        return None
    try:
        data_str = chunk[6:].strip()
        if not data_str or data_str == "[DONE]":
            return None
        event_data = json.loads(data_str)
        usage = event_data.get("usage", {})
        if not usage:
            return None
        prompt = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0
        completion = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0
        total = usage.get("total_tokens", 0) or (prompt + completion)
        return prompt, completion, total
    except Exception:
        return None


def estimate_completion_tokens_from_sse_chunks(chunks: list[str]) -> int:
    estimated_text = []
    for chunk in chunks:
        if not chunk.startswith("data: "):
            continue
        data_str = chunk[6:].strip()
        if not data_str or data_str == "[DONE]":
            continue
        try:
            event_data = json.loads(data_str)
        except Exception:
            continue
        for choice in event_data.get("choices", []) or []:
            delta = choice.get("delta", {}) if isinstance(choice, dict) else {}
            content = delta.get("content") or delta.get("text")
            if isinstance(content, str):
                estimated_text.append(content)
            # Include tool call arguments in completion estimate
            tool_calls = delta.get("tool_calls", [])
            if isinstance(tool_calls, list):
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        func = tc.get("function", {})
                        args = func.get("arguments")
                        if isinstance(args, str):
                            estimated_text.append(args)
        delta = event_data.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("text"), str):
            estimated_text.append(delta["text"])
    return _estimate_text_tokens("".join(estimated_text))


async def read_first_sse_event(line_iter) -> str:
    event_lines = []
    async for line in line_iter:
        if line.strip() == "":
            if event_lines:
                event_text = "\n".join(event_lines) + "\n\n"
                # Skip ping/heartbeat events at the SSE event level
                if _is_ping_sse_event(event_text):
                    event_lines = []
                    continue
                return event_text
            continue
        event_lines.append(line)
    raise httpx.HTTPError("上游流式响应未返回任何 SSE 事件")


async def process_chat_request(request: Request, db: AsyncSession, body: dict, api_format: str = "openai"):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer sk-"):
        raise HTTPException(status_code=401, detail="无效的 API 密钥")
    token_result = await db.execute(select(Token).where(Token.key == auth[7:], Token.status == 1))
    token_obj = token_result.scalar_one_or_none()
    if not token_obj:
        raise HTTPException(status_code=401, detail="无效的 API 密钥")

    if api_format == "bedrock":
        model = body.get("modelId", "anthropic.claude-3-opus-20240229-v1:0")
    else:
        model = body.get("model", "gpt-3.5-turbo")
    is_stream = bool(body.get("stream", False))
    estimated_prompt_tokens = estimate_prompt_tokens(body)
    body, context_info = maybe_compact_context(body, api_format, estimated_prompt_tokens)
    estimated_prompt_tokens = context_info["compacted_estimated_prompt_tokens"]
    request_body_str = _json_dumps(body, ensure_ascii=False)
    log_context = {
        "context_action": context_info["action"],
        "original_estimated_prompt_tokens": context_info["original_estimated_prompt_tokens"],
        "compacted_estimated_prompt_tokens": context_info["compacted_estimated_prompt_tokens"],
    }
    timeout = get_http_timeout(estimated_prompt_tokens)
    start_time = time.time()
    attempts: list[dict] = []
    counted_failure_keys: set[tuple[int, str]] = set()
    last_error: Exception | None = None

    pool_members = await get_pool_members_by_model(db, model)
    requires_vision = _request_requires_vision(body, api_format)

    candidates_by_priority: dict[int, list[tuple[Channel, str, int]]] = {}
    pool_mode = "weighted"
    pool_id_for_rr = None
    if pool_members:
        # Determine pool mode from the first member's pool
        pools = await get_all_pools(db)
        pool = next((p for p in pools if p.name == model), None)
        if pool:
            pool_mode = pool.mode or "weighted"
            pool_id_for_rr = pool.id
        for ch, alias, priority, _weight in pool_members:
            candidates_by_priority.setdefault(priority, []).append((ch, alias, _weight))
    else:
        ch, alias = await get_channel_by_model(db, model)
        if not ch:
            raise HTTPException(status_code=404, detail="无可用渠道")
        candidates_by_priority = {1: [(ch, alias or model, 100)]}

    # Apply load balancing strategy
    token_obj_id = token_obj.id if 'token_obj' in locals() else 0
    candidates_by_priority = _apply_lb_strategy(
        candidates_by_priority, pool_mode, pool_id_for_rr, token_obj_id, model
    )

    # Early detection: no candidates available
    if not candidates_by_priority:
        raise HTTPException(status_code=502, detail="所有候选渠道均不可用 (熔断/软冷却/Vision过滤)")

    # Filter by required capabilities before attempting any channel
    if requires_vision:
        for priority in list(candidates_by_priority.keys()):
            filtered = [
                (ch, alias, weight)
                for ch, alias, weight in candidates_by_priority[priority]
                if _channel_supports_vision(ch, alias)
            ]
            if filtered:
                candidates_by_priority[priority] = filtered
            else:
                del candidates_by_priority[priority]
        if not candidates_by_priority:
            raise HTTPException(status_code=400, detail="当前模型池没有支持图片输入的渠道")

    sorted_priorities = sorted(candidates_by_priority)
    for priority_index, priority in enumerate(sorted_priorities):
        group = weighted_order(candidates_by_priority[priority])
        healthy_group = [(ch, alias, weight) for ch, alias, weight in group if not is_circuit_open(ch.id, alias) and not is_soft_cooldown_open(ch.id, alias)]
        if healthy_group:
            group = healthy_group
        is_primary_priority = priority_index == 0
        max_tries = settings.primary_max_tries if is_primary_priority else settings.backup_max_tries
        max_tries = max(int(max_tries), 1)
        delays = primary_retry_delays() if is_primary_priority else backup_retry_delays()

        for ch, alias, _weight in group:
            if is_xunfei_channel(ch) and estimated_prompt_tokens > settings.xunfei_max_estimated_prompt_tokens:
                last_error = PromptTooLargeForChannel(f"prompt_too_large_for_xunfei:{estimated_prompt_tokens}")
                attempts.append(build_attempt(ch, alias, priority, 0, False, last_error))
                continue
            url, headers, upstream_body = build_upstream_request(ch, alias, model, body, api_format)
            force_non_stream_upstream = settings.force_xunfei_non_stream and is_xunfei_channel(ch)

            for try_idx in range(max_tries):
                if is_circuit_open(ch.id, alias):
                    attempts.append(build_attempt(ch, alias, priority, try_idx, False, "circuit_open"))
                    break
                if is_soft_cooldown_open(ch.id, alias):
                    attempts.append(build_attempt(ch, alias, priority, try_idx, False, "soft_cooldown"))
                    break
                # 本轮重试预算已经接管失败控制，避免全局熔断在第3次失败后提前打断主源5次策略。
                clear_circuit(ch.id, alias)
                if try_idx > 0:
                    await asyncio.sleep(delays[min(try_idx - 1, len(delays) - 1)])
                try:
                    client = get_http_client()
                    if is_stream and force_non_stream_upstream and estimated_prompt_tokens <= settings.force_xunfei_non_stream_max_prompt_tokens:
                        upstream_body = upstream_body.copy()
                        upstream_body["stream"] = False
                        resp = await client.post(url, headers=headers, json=upstream_body, timeout=timeout)
                        resp.raise_for_status()
                        data = parse_json_or_xfyun_data(await resp.aread())
                        raise_for_xfyun_error(data)
                        data = convert_response(data, api_format, ch.api_type)
                        prompt_tokens, completion_tokens, total_tokens = extract_usage(data)
                        if total_tokens == 0:
                            prompt_tokens = estimated_prompt_tokens
                            completion_tokens = estimate_completion_tokens_from_response(data)
                            total_tokens = prompt_tokens + completion_tokens
                        response_body_str = _json_dumps(data, ensure_ascii=False)
                        usage = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens}
                        success_attempt = build_attempt(ch, alias, priority, try_idx, True)
                        attempt_summary = build_attempt_summary(attempts + [success_attempt])

                        async def simulated_stream_with_log():
                            try:
                                if api_format == "openai":
                                    async for chunk in simulate_openai_stream(data, usage):
                                        yield chunk
                                else:
                                    yield response_body_str
                            finally:
                                try:
                                    await resp.aclose()
                                except Exception:
                                    pass
                                record_health_success(ch.id, alias)
                                enqueue_log(
                                    token_id=token_obj.id,
                                    token_name=token_obj.name,
                                    channel_id=ch.id,
                                    channel_name=ch.name,
                                    model=model,
                                    upstream_model=alias,
                                    prompt_tokens=prompt_tokens,
                                    completion_tokens=completion_tokens,
                                    total_tokens=total_tokens,
                                    estimated_prompt_tokens=estimated_prompt_tokens,
                                    estimated_completion_tokens=0,
                                    is_stream=1,
                                    duration_ms=int((time.time() - start_time) * 1000),
                                    first_token_ms=0,
                                    status=1,
                                    error_msg=None,
                                    request_body=request_body_str,
                                    response_body=response_body_str[:100000],
                                    _attempts=attempts + [success_attempt],
                                    **log_context,
                                )

                        return StreamingResponse(simulated_stream_with_log(), media_type="text/event-stream")

                    if is_stream:
                        resp = await client.send(client.build_request("POST", url, headers=headers, json=upstream_body, timeout=timeout), stream=True)
                        try:
                            resp.raise_for_status()
                            content_type = resp.headers.get("content-type", "")
                            if "event-stream" not in content_type:
                                raw_body = await resp.aread()
                                try:
                                    resp_data = parse_json_or_xfyun_data(raw_body)
                                    raise_for_xfyun_error(resp_data)
                                except json.JSONDecodeError:
                                    raise httpx.HTTPError(f"上游返回非流式响应: {raw_body[:500]}")

                            converter = AnthropicSSEToOpenAIConverter() if api_format == "openai" and ch.api_type == "anthropic" else None
                            line_iter = resp.aiter_lines()
                            first_event_text = await read_first_sse_event(line_iter)
                            first_chunk = convert_sse_event(first_event_text, api_format, ch.api_type, converter)
                            # Detect SSE error before sending first chunk to client
                            sse_err = parse_sse_error_from_chunk(first_chunk)
                            if sse_err:
                                err_msg, _err_code = sse_err
                                raise httpx.HTTPError(f"SSE error: {err_msg}")
                            if not first_chunk:
                                raise httpx.HTTPError("上游首个 SSE 事件转换后为空")
                        except Exception:
                            await resp.aclose()
                            raise

                        first_token_time = time.time()
                        response_chunks: list[str] = []
                        prompt_tokens = completion_tokens = total_tokens = 0
                        first_usage = extract_usage_from_sse(first_chunk)
                        if first_usage:
                            prompt_tokens, completion_tokens, total_tokens = first_usage

                        async def stream_with_log():
                            nonlocal first_token_time, prompt_tokens, completion_tokens, total_tokens
                            done_sent = "[DONE]" in first_chunk
                            stream_error = None
                            client_cancelled = False
                            event_lines: list[str] = []
                            try:
                                response_chunks.append(first_chunk)
                                yield first_chunk
                                async for line in line_iter:
                                    if line.strip() == "":
                                        if event_lines:
                                            event_text = "\n".join(event_lines) + "\n\n"
                                            event_lines = []
                                            chunk = convert_sse_event(event_text, api_format, ch.api_type, converter)
                                            if chunk:
                                                response_chunks.append(chunk)
                                                if "[DONE]" in chunk:
                                                    done_sent = True
                                                yield chunk
                                                usage_tuple = extract_usage_from_sse(chunk)
                                                if usage_tuple:
                                                    prompt_tokens, completion_tokens, total_tokens = usage_tuple
                                    else:
                                        event_lines.append(line)
                            except httpx.HTTPError as e:
                                stream_error = str(e) or e.__class__.__name__
                            except asyncio.CancelledError:
                                client_cancelled = True
                                stream_error = "client_cancelled"
                            except Exception as e:
                                stream_error = str(e) or e.__class__.__name__
                            finally:
                                try:
                                    await resp.aclose()
                                except Exception:
                                    pass
                                if event_lines and not client_cancelled:
                                    chunk = "\n".join(event_lines) + "\n\n"
                                    response_chunks.append(chunk)
                                    yield chunk
                                    usage_tuple = extract_usage_from_sse(chunk)
                                    if usage_tuple:
                                        prompt_tokens, completion_tokens, total_tokens = usage_tuple
                                if stream_error and not client_cancelled:
                                    error_chunk = openai_chunk({
                                        "error": {
                                            "message": stream_error,
                                            "type": "stream_error",
                                        }
                                    })
                                    response_chunks.append(error_chunk)
                                    yield error_chunk
                                elif not stream_error and not done_sent:
                                    response_chunks.append("data: [DONE]\n\n")
                                    yield "data: [DONE]\n\n"
                                if total_tokens == 0 and (prompt_tokens or completion_tokens):
                                    total_tokens = prompt_tokens + completion_tokens
                                if not stream_error and total_tokens == 0:
                                    prompt_tokens = estimated_prompt_tokens
                                    completion_tokens = estimate_completion_tokens_from_sse_chunks(response_chunks)
                                    total_tokens = prompt_tokens + completion_tokens
                                status_val = 0 if stream_error else 1
                                if stream_error == "client_cancelled":
                                    status_val = 0
                                elif stream_error:
                                    record_health_failure(ch.id, stream_error, alias)
                                else:
                                    record_health_success(ch.id, alias)
                                observed_attempts = attempts + [build_attempt(ch, alias, priority, try_idx, not stream_error, f"stream_error:{stream_error}" if stream_error else None)]
                                enqueue_log(
                                    token_id=token_obj.id,
                                    token_name=token_obj.name,
                                    channel_id=ch.id,
                                    channel_name=ch.name,
                                    model=model,
                                    upstream_model=alias,
                                    prompt_tokens=prompt_tokens if not stream_error else 0,
                                    completion_tokens=completion_tokens if not stream_error else 0,
                                    total_tokens=total_tokens if not stream_error else 0,
                                    estimated_prompt_tokens=estimated_prompt_tokens,
                                    estimated_completion_tokens=completion_tokens if not stream_error else 0,
                                    is_stream=1,
                                    duration_ms=int((time.time() - start_time) * 1000),
                                    first_token_ms=int((first_token_time - start_time) * 1000) if first_token_time else 0,
                                    status=status_val,
                                    error_type="client_cancelled" if stream_error == "client_cancelled" else ("stream_error_after_start" if stream_error else None),
                                    error_msg=stream_error[:500] if stream_error else None,
                                    request_body=request_body_str,
                                    response_body="".join(response_chunks)[:100000],
                                    _attempts=observed_attempts,
                                    **log_context,
                                )
                                if client_cancelled:
                                    raise asyncio.CancelledError

                        return StreamingResponse(stream_with_log(), media_type="text/event-stream")

                    resp = await client.post(url, headers=headers, json=upstream_body, timeout=timeout)
                    resp.raise_for_status()
                    resp_body = await resp.aread()
                    try:
                        data = parse_json_or_xfyun_data(resp_body)
                        raise_for_xfyun_error(data)
                    except json.JSONDecodeError:
                        raise httpx.HTTPError(f"上游返回非JSON响应: {resp_body[:500]}")
                    data = convert_response(data, api_format, ch.api_type)
                    prompt_tokens, completion_tokens, total_tokens = extract_usage(data)
                    if total_tokens == 0:
                        prompt_tokens = estimated_prompt_tokens
                        completion_tokens = estimate_completion_tokens_from_response(data)
                        total_tokens = prompt_tokens + completion_tokens
                    response_body_str = _json_dumps(data, ensure_ascii=False)
                    record_health_success(ch.id, alias)
                    attempts.append(build_attempt(ch, alias, priority, try_idx, True))
                    enqueue_log(
                        token_id=token_obj.id,
                        token_name=token_obj.name,
                        channel_id=ch.id,
                        channel_name=ch.name,
                        model=model,
                        upstream_model=alias,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        estimated_prompt_tokens=estimated_prompt_tokens,
                        estimated_completion_tokens=0,
                        is_stream=0,
                        duration_ms=int((time.time() - start_time) * 1000),
                        first_token_ms=0,
                        status=1,
                        error_msg=None,
                        request_body=request_body_str,
                        response_body=response_body_str[:100000],
                        _attempts=attempts,
                        **log_context,
                    )
                    return data
                except HTTPException:
                    raise
                except httpx.HTTPError as e:
                    last_error = e
                    error_text = str(e) or e.__class__.__name__
                    # Xfyun SSE errors that are not retryable on the same channel
                    if "SSE error:" in error_text and not is_xfyun_error_retryable(error_text):
                        attempts.append(build_attempt(ch, alias, priority, try_idx, False, e))
                        break
                    if should_count_failure(e, estimated_prompt_tokens):
                        failure_key = (ch.id, alias or model)
                        should_disable = False
                        if failure_key not in counted_failure_keys:
                            counted_failure_keys.add(failure_key)
                            should_disable = record_health_failure(ch.id, error_text, alias)
                        if should_disable:
                            # Model-level circuit breakers should not disable the whole channel.
                            pass
                        attempts.append(build_attempt(ch, alias, priority, try_idx, False, e))
                        if try_idx < max_tries - 1:
                            continue
                    else:
                        attempts.append(build_attempt(ch, alias, priority, try_idx, False, f"ReadTimeout(heavy:{estimated_prompt_tokens})"))
                        record_health_soft_failure(ch.id, f"ReadTimeout(heavy:{estimated_prompt_tokens})", alias, settings.heavy_timeout_soft_cooldown)
                        break
                    break

    attempt_summary = build_attempt_summary(attempts)
    enqueue_log(
        token_id=token_obj.id,
        token_name=token_obj.name,
        channel_id=None,
        model=model,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        estimated_prompt_tokens=estimated_prompt_tokens,
        estimated_completion_tokens=0,
        is_stream=1 if is_stream else 0,
        duration_ms=int((time.time() - start_time) * 1000),
        first_token_ms=0,
        status=0,
        error_type=classify_error(last_error) if last_error else None,
        error_msg=(attempt_summary or (str(last_error) if last_error else "所有上游渠道均不可用"))[:500],
        request_body=request_body_str,
        _attempts=attempts,
        **log_context,
    )
    if isinstance(last_error, PromptTooLargeForChannel):
        raise HTTPException(status_code=413, detail=str(last_error))
    raise HTTPException(status_code=502, detail=f"上游错误: {str(last_error)}" if last_error else "所有上游渠道均不可用")


@router.post("/v1/chat/completions")
async def chat_completions(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        return await process_chat_request(request, db, body, api_format="openai")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERROR in chat_completions: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.post("/v1/messages")
async def anthropic_messages(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        return await process_chat_request(request, db, body, api_format="anthropic")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERROR in anthropic_messages: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


# ==================== P2-3: API 兼容层 ====================

async def _process_generic_request(request: Request, db: AsyncSession, body: dict, endpoint: str):
    """处理通用非流式 API 请求（embeddings / images/generations）。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer sk-"):
        raise HTTPException(status_code=401, detail="无效的 API 密钥")
    token_obj = await get_token_by_key(db, auth[7:])
    if not token_obj:
        raise HTTPException(status_code=401, detail="无效的 API 密钥")

    model = body.get("model", "")
    if not model:
        raise HTTPException(status_code=400, detail="缺少 model 字段")

    pool_members = await get_pool_members_by_model(db, model)
    if pool_members:
        ch, alias, _, _ = pool_members[0]
    else:
        ch, alias = await get_channel_by_model(db, model)
    if not ch:
        raise HTTPException(status_code=404, detail="无可用渠道")

    url = f"{ch.base_url}{endpoint}"
    headers = {"Authorization": f"Bearer {ch.api_key}", "Content-Type": "application/json"}
    upstream_body = body.copy()
    if "model" in upstream_body and alias:
        upstream_body["model"] = alias

    timeout = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)
    client = get_http_client()
    start_time = time.time()
    try:
        resp = await client.post(url, headers=headers, json=upstream_body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        error_body = e.response.text[:500] if e.response else str(e)
        raise HTTPException(status_code=e.response.status_code if e.response else 502, detail=error_body)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"上游请求失败: {str(e)[:500]}")

    duration_ms = int((time.time() - start_time) * 1000)
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    if isinstance(data, dict) and "usage" in data and isinstance(data["usage"], dict):
        usage = data["usage"]
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

    enqueue_log(
        token_id=token_obj.id,
        token_name=token_obj.name,
        channel_id=ch.id,
        channel_name=ch.name,
        model=model,
        upstream_model=alias or model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_prompt_tokens=0,
        estimated_completion_tokens=0,
        is_stream=0,
        duration_ms=duration_ms,
        first_token_ms=duration_ms,
        status=1,
        error_type=None,
        error_msg=None,
        retry_count=0,
        fallback_used=0,
        request_body=_json_dumps(body, ensure_ascii=False),
        response_body=_json_dumps(data, ensure_ascii=False)[:8000],
        attempts_json=None,
    )
    return data


@router.post("/v1/embeddings")
async def create_embeddings(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        return await _process_generic_request(request, db, body, "/v1/embeddings")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERROR in create_embeddings: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.post("/v1/images/generations")
async def create_images(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        return await _process_generic_request(request, db, body, "/v1/images/generations")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERROR in create_images: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.get("/api/dashboard/stats")
async def dashboard_stats(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)

    # Use pre-aggregated stats_daily for fast totals (single query)
    today_str = datetime.now().strftime("%Y-%m-%d")
    seven_days_ago = datetime.now() - timedelta(days=7)

    # Get today's stats from stats_daily (instant lookup)
    today_result = await db.execute(select(StatsDaily).where(StatsDaily.date == today_str))
    today_row = today_result.scalar_one_or_none()

    # Get 7-day stats from stats_daily for totals
    seven_days = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        seven_days.append(d)
    daily_result = await db.execute(
        select(StatsDaily).where(StatsDaily.date.in_(seven_days)).order_by(StatsDaily.date)
    )
    daily_rows = {r.date: r for r in daily_result.scalars().all()}

    # Aggregate totals from stats_daily (fast)
    total_requests = sum(r.request_count for r in daily_rows.values())
    success_requests = sum(r.success_count for r in daily_rows.values())
    failed_requests = sum(r.fail_count for r in daily_rows.values())
    total_tokens = sum(r.input_tokens + r.output_tokens for r in daily_rows.values())
    prompt_tokens = sum(r.input_tokens for r in daily_rows.values())
    completion_tokens = sum(r.output_tokens for r in daily_rows.values())

    # Trend from request_logs (uses created_at index, accurate for all historical data)
    request_scope = final_request_filter()
    trend_result = await db.execute(
        select(func.date(RequestLog.created_at).label("date"), func.count(RequestLog.id).label("count"))
        .where(request_scope, RequestLog.created_at >= seven_days_ago)
        .group_by(func.date(RequestLog.created_at))
        .order_by(func.date(RequestLog.created_at))
    )
    trend_map = {str(row[0]): row[1] for row in trend_result.all()}
    trend = [{"date": d, "count": trend_map.get(d, 0)} for d in seven_days]

    # Today stats
    today_requests = today_row.request_count if today_row else 0
    failure_rate = round((failed_requests / total_requests) * 100, 2) if total_requests else 0

    # Success/failed token breakdown: need raw logs query (only for these 2 fields)
    request_scope = final_request_filter()
    success_tokens_result = await db.execute(
        select(func.sum(RequestLog.total_tokens)).where(request_scope, RequestLog.status == 1)
    )
    success_tokens = success_tokens_result.scalar() or 0
    success_prompt_tokens_result = await db.execute(
        select(func.sum(RequestLog.prompt_tokens)).where(request_scope, RequestLog.status == 1)
    )
    success_prompt_tokens = success_prompt_tokens_result.scalar() or 0
    success_completion_tokens_result = await db.execute(
        select(func.sum(RequestLog.completion_tokens)).where(request_scope, RequestLog.status == 1)
    )
    success_completion_tokens = success_completion_tokens_result.scalar() or 0

    # Estimated tokens from raw logs (single combined query)
    est_all_result = await db.execute(
        select(
            func.sum(RequestLog.estimated_prompt_tokens),
            func.sum(RequestLog.estimated_completion_tokens),
        ).where(request_scope)
    )
    est_all = est_all_result.one_or_none()
    estimated_prompt_tokens = est_all[0] or 0 if est_all else 0
    estimated_completion_tokens = est_all[1] or 0 if est_all else 0
    estimated_tokens = estimated_prompt_tokens + estimated_completion_tokens

    est_fail_result = await db.execute(
        select(
            func.sum(RequestLog.estimated_prompt_tokens),
            func.sum(RequestLog.estimated_completion_tokens),
        ).where(request_scope, RequestLog.status == 0)
    )
    est_fail = est_fail_result.one_or_none()
    failed_estimated_prompt_tokens = est_fail[0] or 0 if est_fail else 0
    failed_estimated_completion_tokens = est_fail[1] or 0 if est_fail else 0
    failed_estimated_tokens = failed_estimated_prompt_tokens + failed_estimated_completion_tokens

    # Fast lookups (not from logs)
    active_channels_result = await db.execute(select(func.count(Channel.id)).where(Channel.status == 1))
    active_channels = active_channels_result.scalar() or 0
    total_api_keys_result = await db.execute(select(func.count(Token.id)))
    total_api_keys = total_api_keys_result.scalar() or 0

    # Model distribution from stats_model (pre-aggregated, instant)
    model_dist_result = await db.execute(
        select(StatsModel.model_name, StatsModel.request_count)
        .order_by(StatsModel.request_count.desc()).limit(10)
    )
    model_distribution = [{"model": r[0], "count": r[1]} for r in model_dist_result.all()]

    return {
        "success": True,
        "data": {
            "total_requests": total_requests,
            "today_requests": today_requests,
            "success_requests": success_requests,
            "failed_requests": failed_requests,
            "failure_rate": failure_rate,
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "success_tokens": success_tokens,
            "success_prompt_tokens": success_prompt_tokens,
            "success_completion_tokens": success_completion_tokens,
            "estimated_tokens": estimated_tokens,
            "estimated_prompt_tokens": estimated_prompt_tokens,
            "estimated_completion_tokens": estimated_completion_tokens,
            "failed_estimated_tokens": failed_estimated_tokens,
            "failed_estimated_prompt_tokens": failed_estimated_prompt_tokens,
            "failed_estimated_completion_tokens": failed_estimated_completion_tokens,
            "active_channels": active_channels,
            "total_api_keys": total_api_keys,
            "trend": trend,
            "model_distribution": model_distribution,
        },
    }


# ==================== P2-1: 管理后台增强 ====================

@router.post("/api/channels/batch-update")
async def batch_update_channels(data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    ids = data.get("ids", [])
    status = data.get("status")
    if not ids:
        raise HTTPException(status_code=400, detail="未指定渠道ID")
    if status not in (0, 1):
        raise HTTPException(status_code=400, detail="status 必须为 0 或 1")
    await db.execute(update(Channel).where(Channel.id.in_(ids)).values(status=status))
    await db.commit()
    invalidate_channels()
    return {"success": True, "message": f"已更新 {len(ids)} 个渠道"}


@router.post("/api/channels/batch-delete")
async def batch_delete_channels(data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="未指定渠道ID")
    await db.execute(delete(PoolMember).where(PoolMember.channel_id.in_(ids)))
    await db.execute(delete(Channel).where(Channel.id.in_(ids)))
    await db.commit()
    invalidate_channels()
    invalidate_pools()
    return {"success": True, "message": f"已删除 {len(ids)} 个渠道"}


@router.post("/api/tokens/batch-update")
async def batch_update_tokens(data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    ids = data.get("ids", [])
    status = data.get("status")
    if not ids:
        raise HTTPException(status_code=400, detail="未指定令牌ID")
    if status not in (0, 1):
        raise HTTPException(status_code=400, detail="status 必须为 0 或 1")
    await db.execute(update(Token).where(Token.id.in_(ids)).values(status=status))
    await db.commit()
    return {"success": True, "message": f"已更新 {len(ids)} 个令牌"}


@router.post("/api/tokens/batch-delete")
async def batch_delete_tokens(data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="未指定令牌ID")
    result = await db.execute(select(Token).where(Token.id.in_(ids)))
    for token in result.scalars().all():
        invalidate_token(token.key)
    await db.execute(delete(Token).where(Token.id.in_(ids)))
    await db.commit()
    return {"success": True, "message": f"已删除 {len(ids)} 个令牌"}


@router.get("/api/config/export")
async def export_config(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    channels_result = await db.execute(select(Channel).order_by(Channel.id))
    channels = []
    for ch in channels_result.scalars().all():
        channels.append({
            "id": ch.id,
            "name": ch.name,
            "base_url": ch.base_url,
            "api_key": ch.api_key,
            "models": ch.models,
            "api_type": ch.api_type,
            "status": ch.status,
        })
    tokens_result = await db.execute(select(Token).order_by(Token.id))
    tokens = []
    for t in tokens_result.scalars().all():
        tokens.append({
            "id": t.id,
            "name": t.name,
            "key": t.key,
            "status": t.status,
        })
    pools_result = await db.execute(select(ModelPool).order_by(ModelPool.id))
    pools = []
    for p in pools_result.scalars().all():
        pools.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "status": p.status,
        })
    members_result = await db.execute(select(PoolMember).order_by(PoolMember.id))
    members = []
    for m in members_result.scalars().all():
        members.append({
            "id": m.id,
            "pool_id": m.pool_id,
            "channel_id": m.channel_id,
            "alias": m.alias,
            "weight": m.weight,
            "priority": m.priority,
            "status": m.status,
        })
    return {
        "success": True,
        "data": {
            "channels": channels,
            "tokens": tokens,
            "model_pools": pools,
            "pool_members": members,
        },
    }


@router.post("/api/config/import")
async def import_config(data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    channels = data.get("channels", [])
    tokens = data.get("tokens", [])
    pools = data.get("model_pools", [])
    members = data.get("pool_members", [])
    created_channels = 0
    created_tokens = 0
    created_pools = 0
    created_members = 0
    for ch_data in channels:
        ch = Channel(
            name=ch_data.get("name", ""),
            base_url=(ch_data.get("base_url") or "").rstrip("/"),
            api_key=ch_data.get("api_key", ""),
            models=ch_data.get("models", ""),
            api_type=ch_data.get("api_type", "openai"),
            status=ch_data.get("status", 1),
        )
        db.add(ch)
        created_channels += 1
    for t_data in tokens:
        t = Token(
            name=t_data.get("name", "default"),
            key=t_data.get("key", "sk-" + __import__("secrets").token_urlsafe(32)),
            status=t_data.get("status", 1),
        )
        db.add(t)
        created_tokens += 1
    for p_data in pools:
        p = ModelPool(
            name=p_data.get("name", ""),
            description=p_data.get("description", ""),
            status=p_data.get("status", 1),
        )
        db.add(p)
        created_pools += 1
    for m_data in members:
        m = PoolMember(
            pool_id=m_data.get("pool_id"),
            channel_id=m_data.get("channel_id"),
            alias=m_data.get("alias", ""),
            weight=m_data.get("weight", 100),
            priority=m_data.get("priority", 1),
            status=m_data.get("status", 1),
        )
        db.add(m)
        created_members += 1
    await db.commit()
    invalidate_all()
    return {
        "success": True,
        "message": f"导入完成: 渠道 {created_channels}, 令牌 {created_tokens}, 模型池 {created_pools}, 成员 {created_members}",
    }


@router.post("/api/logs/{log_id}/replay")
async def replay_log(log_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(RequestLog).where(RequestLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    if not log.request_body:
        raise HTTPException(status_code=400, detail="日志无请求体，无法重放")
    try:
        body = json.loads(log.request_body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"请求体解析失败: {str(e)}")
    model = body.get("model", "")
    if not model:
        raise HTTPException(status_code=400, detail="请求体中缺少 model 字段")
    stream = body.get("stream", False)
    # 查找模型池或渠道
    candidates = await get_pool_members_by_model(db, model)
    if not candidates:
        ch, upstream_model = await get_channel_by_model(db, model)
        if not ch:
            raise HTTPException(status_code=404, detail="无可用渠道重放该请求")
        candidates = [(ch, upstream_model or model, 1, 100)]
    ch, alias, _, _ = candidates[0]
    url, headers, upstream_body = build_upstream_request(ch, alias, model, body, "openai")
    timeout = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)
    client = get_http_client()
    try:
        resp = await client.post(url, headers=headers, json=upstream_body, timeout=timeout)
        resp.raise_for_status()
        resp_body = resp.json()
    except Exception as e:
        return {"success": False, "message": f"重放失败: {str(e)[:500]}", "status_code": getattr(resp, "status_code", 0)}
    return {
        "success": True,
        "message": "重放成功",
        "status_code": resp.status_code,
        "response": resp_body,
    }


# ==================== P2-2: 配置热更新 ====================

@router.post("/api/config/reload")
async def reload_config(request: Request):
    require_admin(request)
    reloaded = reload_settings()
    invalidate_all()
    return {"success": True, "message": "配置已重载" if reloaded else "配置无变更"}


# ==================== Image Generation ====================

@router.post("/api/image-generations")
async def image_generations(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    body = await request.json()
    
    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="缺少 prompt 参数")
    
    model = body.get("model", "gpt-image-2")
    n = body.get("n", 1)
    size = body.get("size", "1024x1024")
    quality = body.get("quality", "standard")
    style = body.get("style", "vivid")
    
    # Find JMR OpenAI channel for image generation
    result = await db.execute(
        select(Channel).where(
            Channel.name == "jmr-openai",
            Channel.status == 1
        )
    )
    ch = result.scalar_one_or_none()
    
    if not ch:
        # Fallback to any openai channel that supports image models
        result = await db.execute(
            select(Channel).where(
                Channel.api_type == "openai",
                Channel.status == 1
            )
        )
        ch = result.scalar_one_or_none()
    
    if not ch:
        raise HTTPException(status_code=404, detail="无可用图片生成渠道")
    
    url = f"{ch.base_url}/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {ch.api_key}",
        "Content-Type": "application/json"
    }
    upstream_body = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size,
        "quality": quality,
        "style": style
    }
    
    client = get_http_client()
    try:
        # Image generation may take 60-180 seconds
        resp = await client.post(url, headers=headers, json=upstream_body, timeout=300.0)
        resp.raise_for_status()
        data = resp.json()
        # Convert b64_json to data URL if needed
        if "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                if "b64_json" in item and "url" not in item:
                    item["url"] = f"data:image/png;base64,{item['b64_json']}"
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as e:
        error_body = e.response.text[:500]
        raise HTTPException(status_code=502, detail=f"上游错误: {error_body}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"请求失败: {str(e)[:500]}")


@router.post("/api/image-edits")
async def image_edits(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    body = await request.json()

    prompt = body.get("prompt", "")
    image_data = body.get("image", "")

    if not prompt:
        raise HTTPException(status_code=400, detail="缺少 prompt 参数")
    if not image_data:
        raise HTTPException(status_code=400, detail="缺少 image 参数")

    model = body.get("model", "gpt-image-2")
    size = body.get("size", "1024x1024")

    # Find JMR OpenAI channel for image editing
    result = await db.execute(
        select(Channel).where(
            Channel.name == "jmr-openai",
            Channel.status == 1
        )
    )
    ch = result.scalar_one_or_none()

    if not ch:
        result = await db.execute(
            select(Channel).where(
                Channel.api_type == "openai",
                Channel.status == 1
            )
        )
        ch = result.scalar_one_or_none()

    if not ch:
        raise HTTPException(status_code=404, detail="无可用图片编辑渠道")

    # Parse base64 image data
    if image_data.startswith("data:image"):
        header, b64 = image_data.split(",", 1)
        image_bytes = base64.b64decode(b64)
    else:
        raise HTTPException(status_code=400, detail="图片格式不正确，需要 base64 data URL")

    # Convert image to PNG, square, and max 4MB for OpenAI edits API
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        # Convert to RGBA to preserve transparency, or RGB if no alpha
        if img.mode in ('RGBA', 'LA', 'P'):
            # For edits API, we need a background; use white for transparency
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        else:
            img = img.convert('RGB')
        # Make square by center cropping to the smaller dimension
        w, h = img.size
        min_dim = min(w, h)
        left = (w - min_dim) // 2
        top = (h - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))
        # Resize to 1024x1024 (OpenAI recommended size for edits)
        img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
        # Save as PNG
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        image_bytes = buf.getvalue()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片处理失败: {str(e)}")

    url = f"{ch.base_url}/v1/images/edits"
    headers = {
        "Authorization": f"Bearer {ch.api_key}"
    }

    # Build multipart form data using pure 'files' dict (httpx handles boundary)
    files = {
        "image": ("image.png", image_bytes, "image/png"),
        "prompt": (None, prompt),
        "model": (None, model),
        "size": (None, size),
        "n": (None, "1")
    }

    client = get_http_client()
    try:
        resp = await client.post(url, headers=headers, files=files, timeout=300.0)
        resp.raise_for_status()
        data = resp.json()
        # Convert b64_json to data URL if needed
        if "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                if "b64_json" in item and "url" not in item:
                    item["url"] = f"data:image/png;base64,{item['b64_json']}"
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as e:
        error_body = e.response.text[:500]
        raise HTTPException(status_code=502, detail=f"上游错误: {error_body}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"请求失败: {str(e)[:500]}")


@router.get("/api/image-models")
async def get_image_models(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    return {
        "success": True,
        "data": [
            {"id": "gpt-image-2", "name": "GPT Image 2", "sizes": ["1024x1024", "1024x1792", "1792x1024"], "qualities": ["standard", "hd"]},
            {"id": "gpt-image-1", "name": "GPT Image 1", "sizes": ["1024x1024", "1024x1792", "1792x1024"], "qualities": ["standard", "hd"]},
        ]
    }


# ============================================================
# Statistics APIs
# ============================================================

@router.get("/api/stats/daily")
async def get_daily_stats(request: Request, db: AsyncSession = Depends(get_db), days: int = 7):
    require_admin(request)
    from datetime import datetime, timedelta
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]
    result = await db.execute(select(StatsDaily).where(StatsDaily.date.in_(dates)).order_by(StatsDaily.date))
    rows = result.scalars().all()
    data_map = {r.date: r for r in rows}
    data = []
    for d in dates:
        r = data_map.get(d)
        data.append({
            "date": d,
            "request_count": r.request_count if r else 0,
            "success_count": r.success_count if r else 0,
            "fail_count": r.fail_count if r else 0,
            "input_tokens": r.input_tokens if r else 0,
            "output_tokens": r.output_tokens if r else 0,
        })
    return {"success": True, "data": data}


@router.get("/api/stats/hourly")
async def get_hourly_stats(request: Request, db: AsyncSession = Depends(get_db), hours: int = 24):
    require_admin(request)
    from datetime import datetime, timedelta
    now = datetime.now()
    hour_list = [(now - timedelta(hours=i)).strftime("%Y-%m-%d_%H") for i in range(hours - 1, -1, -1)]
    result = await db.execute(select(StatsHourly).where(StatsHourly.hour.in_(hour_list)).order_by(StatsHourly.hour))
    rows = result.scalars().all()
    data_map = {r.hour: r for r in rows}
    data = []
    for h in hour_list:
        r = data_map.get(h)
        data.append({
            "hour": h,
            "request_count": r.request_count if r else 0,
            "success_count": r.success_count if r else 0,
            "fail_count": r.fail_count if r else 0,
            "input_tokens": r.input_tokens if r else 0,
            "output_tokens": r.output_tokens if r else 0,
        })
    return {"success": True, "data": data}


@router.get("/api/stats/models")
async def get_model_stats(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(StatsModel).order_by(StatsModel.request_count.desc()))
    rows = result.scalars().all()
    return {"success": True, "data": [{"model_name": r.model_name, "request_count": r.request_count,
            "input_tokens": r.input_tokens, "output_tokens": r.output_tokens} for r in rows]}


@router.get("/api/stats/channels")
async def get_channel_stats(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(StatsChannel).order_by(StatsChannel.request_count.desc()))
    rows = result.scalars().all()
    ch_result = await db.execute(select(Channel.id, Channel.name))
    ch_map = {cid: name for cid, name in ch_result.all()}
    return {"success": True, "data": [{"channel_id": r.channel_id, "channel_name": ch_map.get(r.channel_id, "未知"),
            "request_count": r.request_count, "success_count": r.success_count, "fail_count": r.fail_count,
            "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
            "avg_first_token_ms": r.avg_first_token_ms} for r in rows]}


@router.get("/api/stats/tokens")
async def get_token_stats(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(StatsToken).order_by(StatsToken.request_count.desc()))
    rows = result.scalars().all()
    tk_result = await db.execute(select(Token.id, Token.name))
    tk_map = {tid: name for tid, name in tk_result.all()}
    return {"success": True, "data": [{"token_id": r.token_id, "token_name": tk_map.get(r.token_id, "未知"),
            "request_count": r.request_count, "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens} for r in rows]}


# ============================================================
# Model Sync
# ============================================================

@router.post("/api/channels/{channel_id}/sync-models")
async def sync_channel_models(channel_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="渠道不存在")
    # Normalize base URL (same logic as build_upstream_request)
    base_url = (ch.base_url or "").rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3].rstrip("/")
    url = f"{base_url}/v1/models"
    headers = {"Authorization": f"Bearer {ch.api_key}"}
    client = get_http_client()
    try:
        resp = await client.get(url, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        models = [m["id"] for m in data.get("data", []) if "id" in m]
        if models:
            ch.models = ",".join(models)
            await db.commit()
            invalidate_channels()
        return {"success": True, "data": {"models": models, "count": len(models)}}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"同步失败: {str(e)[:500]}")
