from typing import Annotated, Optional

from fastapi import Header, HTTPException, status

from .config import get_settings


async def verify_api_key(x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None) -> None:
    settings = get_settings()
    if settings.mintagent_api_key:
        if x_api_key != settings.mintagent_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

