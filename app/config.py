import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")
    
    port: int = 3000
    debug: bool = False
    db_url: str = "sqlite+aiosqlite:///./data/coapi.db"
    jwt_secret: str = "co-api-secret-change-me-please"
    jwt_expiry: int = 30  # days

    # Relay retry/fallback settings
    retry_prompt_threshold: int = 500
    primary_max_tries: int = 5
    backup_max_tries: int = 2
    primary_retry_delays: str = "2,3,4,5"
    backup_retry_delays: str = "2"
    connect_timeout: float = 10.0
    read_timeout_light: float = 120.0
    read_timeout_heavy: float = 300.0
    heavy_timeout_soft_cooldown: float = 30.0
    write_timeout: float = 30.0
    pool_timeout: float = 10.0
    context_overflow_policy: str = "route_only"
    auto_compact_enabled: bool = False
    auto_compact_trigger_tokens: int = 140000
    auto_compact_target_tokens: int = 120000
    compact_preserve_recent_messages: int = 8
    compact_summary_max_chars: int = 12000
    xunfei_max_estimated_prompt_tokens: int = 180000
    force_xunfei_non_stream: bool = True
    force_xunfei_non_stream_max_prompt_tokens: int = 20000

    # Log retention settings
    log_body_retention_count: int = 500
    log_cleanup_interval: int = 100

    # Cache TTL
    channel_cache_ttl: int = 30  # seconds
    
settings = Settings()

_env_file_path = os.path.abspath(".env")
_env_file_mtime = 0.0

def _get_env_mtime():
    try:
        return os.path.getmtime(_env_file_path)
    except OSError:
        return 0.0

_env_file_mtime = _get_env_mtime()

def reload_settings():
    global settings, _env_file_mtime
    settings = Settings()
    _env_file_mtime = _get_env_mtime()

def check_settings_reload():
    global _env_file_mtime
    current = _get_env_mtime()
    if current > _env_file_mtime:
        reload_settings()
        return True
    return False
