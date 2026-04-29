from sqlalchemy import Column, Integer, String, DateTime, Text, Float, func, Index, UniqueConstraint
from app.database import Base

# NOTE: LLMPrice model removed per user request

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, default="admin")
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    base_url = Column(String(512), nullable=False, default="https://api.openai.com")
    api_key = Column(String(512), nullable=False, default="")
    models = Column(String(2048), nullable=False, default="gpt-3.5-turbo")
    api_type = Column(String(32), nullable=False, default="openai")
    status = Column(Integer, default=1)
    custom_headers = Column(Text, nullable=True)
    proxy_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Token(Base):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False, default="default")
    status = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, nullable=True, index=True)
    token_name = Column(String(128), nullable=True)
    channel_id = Column(Integer, nullable=True, index=True)
    channel_name = Column(String(128), nullable=True)
    model = Column(String(128), nullable=True, index=True)
    upstream_model = Column(String(128), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_prompt_tokens = Column(Integer, default=0)
    estimated_completion_tokens = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    first_token_ms = Column(Integer, default=0)
    is_stream = Column(Integer, default=0)
    status = Column(Integer, default=1)
    error_type = Column(String(64), nullable=True)
    retry_count = Column(Integer, default=0)
    fallback_used = Column(Integer, default=0)
    attempts_json = Column(Text, nullable=True)
    context_action = Column(String(64), nullable=True)
    original_estimated_prompt_tokens = Column(Integer, default=0)
    compacted_estimated_prompt_tokens = Column(Integer, default=0)
    error_msg = Column(String(512), nullable=True)
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('ix_request_log_composite', 'token_id', 'model', 'created_at'),
        Index('ix_request_log_channel', 'channel_id', 'created_at'),
        Index('ix_request_log_status_created', 'status', 'created_at'),
    )

class ModelPool(Base):
    __tablename__ = "model_pools"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True)
    description = Column(String(512), nullable=True)
    mode = Column(String(32), nullable=False, default="weighted")
    status = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

class PoolMember(Base):
    __tablename__ = "pool_members"
    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, nullable=False, index=True)
    channel_id = Column(Integer, nullable=False, index=True)
    alias = Column(String(128), nullable=True)
    weight = Column(Integer, default=100)
    priority = Column(Integer, default=1)
    status = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

class StatsHourly(Base):
    __tablename__ = "stats_hourly"
    id = Column(Integer, primary_key=True, index=True)
    hour = Column(String(13), nullable=False, index=True)
    request_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    avg_duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint('hour', name='uq_stats_hourly_hour'),)

class StatsDaily(Base):
    __tablename__ = "stats_daily"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), nullable=False, unique=True, index=True)
    request_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    avg_duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class StatsModel(Base):
    __tablename__ = "stats_model"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(128), nullable=False, index=True)
    request_count = Column(Integer, default=0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint('model_name', name='uq_stats_model_name'),)

class StatsChannel(Base):
    __tablename__ = "stats_channel"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, nullable=False, unique=True, index=True)
    request_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    avg_first_token_ms = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class StatsToken(Base):
    __tablename__ = "stats_token"
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, nullable=False, unique=True, index=True)
    request_count = Column(Integer, default=0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class HealthSnapshot(Base):
    __tablename__ = "health_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    health_key = Column(String(64), nullable=False, unique=True, index=True)
    consecutive_failures = Column(Integer, default=0)
    cooldown_until = Column(Float, default=0.0)
    soft_cooldown_until = Column(Float, default=0.0)
    last_error = Column(String(256), nullable=True)
    total_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    last_success_time = Column(Float, default=0.0)
    last_error_time = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())