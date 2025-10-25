import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

rate_per_minute = os.getenv("RATE_LIMIT_PER_MINUTE", "120")

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{rate_per_minute}/minute"]) 

async def rate_limit_handler(request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
