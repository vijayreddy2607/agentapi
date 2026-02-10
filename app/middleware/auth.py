"""API key authentication middleware."""
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def verify_api_key(request: Request):
    """Verify API key from request header."""
    api_key = request.headers.get("x-api-key")
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include 'x-api-key' in request headers."
        )
    
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key."
        )
    
    return api_key
