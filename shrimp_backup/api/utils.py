"""Response utilities for converting ServiceResponse to FastAPI responses."""

from typing import Any, TypeVar, Generic
from fastapi import HTTPException
from shrimp.core.response import ServiceResponse

T = TypeVar('T')


def handle_service_response(response: ServiceResponse[T]) -> T:
    """Convert ServiceResponse to FastAPI response or raise HTTPException."""
    if response.success:
        return response.data
    
    # Map service response codes to FastAPI HTTP status codes
    status_code = response.code
    if status_code == 200:  # Default error code
        status_code = 400
    
    raise HTTPException(
        status_code=status_code,
        detail=response.error or "Unknown error occurred"
    )