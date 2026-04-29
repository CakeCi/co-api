from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

engine = create_async_engine(settings.db_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Create default admin user if none exists
    async with SessionLocal() as session:
        from sqlalchemy import select, func
        from app.models import User
        from app.core.security import hash_password
        result = await session.execute(select(func.count(User.id)))
        count = result.scalar() or 0
        if count == 0:
            default_user = User(
                username="admin",
                password_hash=hash_password("Admin@1234")
            )
            session.add(default_user)
            await session.commit()
    # SQLite schema migration: add missing columns if not present
    async with engine.begin() as conn:
        from sqlalchemy import text
        # Check columns in request_logs
        result = await conn.execute(text("PRAGMA table_info(request_logs)"))
        columns = {row[1] for row in result.fetchall()}
        if "estimated_prompt_tokens" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN estimated_prompt_tokens INTEGER DEFAULT 0"))
        if "estimated_completion_tokens" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN estimated_completion_tokens INTEGER DEFAULT 0"))
        if "channel_name" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN channel_name VARCHAR(128)"))
        if "upstream_model" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN upstream_model VARCHAR(128)"))
        if "error_type" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN error_type VARCHAR(64)"))
        if "retry_count" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN retry_count INTEGER DEFAULT 0"))
        if "fallback_used" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN fallback_used INTEGER DEFAULT 0"))
        if "attempts_json" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN attempts_json TEXT"))
        if "context_action" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN context_action VARCHAR(64)"))
        if "original_estimated_prompt_tokens" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN original_estimated_prompt_tokens INTEGER DEFAULT 0"))
        if "compacted_estimated_prompt_tokens" not in columns:
            await conn.execute(text("ALTER TABLE request_logs ADD COLUMN compacted_estimated_prompt_tokens INTEGER DEFAULT 0"))
        
        # Check columns in channels
        result = await conn.execute(text("PRAGMA table_info(channels)"))
        ch_columns = {row[1] for row in result.fetchall()}
        if "custom_headers" not in ch_columns:
            await conn.execute(text("ALTER TABLE channels ADD COLUMN custom_headers TEXT"))
        if "proxy_url" not in ch_columns:
            await conn.execute(text("ALTER TABLE channels ADD COLUMN proxy_url VARCHAR(512)"))
        
        # Check columns in model_pools
        result = await conn.execute(text("PRAGMA table_info(model_pools)"))
        pool_columns = {row[1] for row in result.fetchall()}
        if "mode" not in pool_columns:
            await conn.execute(text("ALTER TABLE model_pools ADD COLUMN mode VARCHAR(32) DEFAULT 'weighted'"))
        
        # Create performance indexes
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_request_log_created_at ON request_logs(created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_request_log_channel_id ON request_logs(channel_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pool_members_channel_id ON pool_members(channel_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_request_log_composite ON request_logs(token_id, model, created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_request_log_channel_created ON request_logs(channel_id, created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_request_log_status_created ON request_logs(status, created_at)"))