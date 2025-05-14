import os

from dotenv import load_dotenv
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

limiter = Limiter(
    key_func=get_remote_address,
    headers_enabled=True,
    default_limits=[os.getenv("RATELIMIT_DEFAULT", "3 per minute")],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)

cache = Cache(
    config={
        "CACHE_TYPE": "RedisCache",
        "CACHE_REDIS_URL": "redis://localhost:6379/0",
        "CACHE_DEFAULT_TIMEOUT": 60,
    }
)
