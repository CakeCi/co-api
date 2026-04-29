import httpx
from app.config import settings

_shared_client: httpx.AsyncClient | None = None


def init_http_client() -> httpx.AsyncClient:
    """初始化全局共享的 httpx AsyncClient（连接池复用）。"""
    global _shared_client
    if _shared_client is None:
        limits = httpx.Limits(
            max_connections=200,
            max_keepalive_connections=20,
            keepalive_expiry=30.0,
        )
        timeout = httpx.Timeout(
            connect=settings.connect_timeout,
            read=max(settings.read_timeout_light, settings.read_timeout_heavy),
            write=settings.write_timeout,
            pool=settings.pool_timeout,
        )
        _shared_client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            http2=True,
        )
    return _shared_client


def get_http_client() -> httpx.AsyncClient:
    """获取全局共享 client，若未初始化则自动创建。"""
    if _shared_client is None:
        return init_http_client()
    return _shared_client


async def close_http_client():
    """关闭全局共享 client，用于应用 shutdown。"""
    global _shared_client
    if _shared_client is not None:
        await _shared_client.aclose()
        _shared_client = None
