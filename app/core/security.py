import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.config import settings

SECRET_KEY = settings.jwt_secret
ALGORITHM = "HS256"

def hash_password(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

def verify_password(pwd: str, hashed: str) -> bool:
    return bcrypt.checkpw(pwd.encode(), hashed.encode())

def create_token(data: dict, days: int | None = None) -> str:
    from app.config import settings
    to_encode = data.copy()
    expiry_days = days if days is not None else settings.jwt_expiry
    expire = datetime.now(timezone.utc) + timedelta(days=expiry_days)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None
