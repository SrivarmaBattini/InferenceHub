# schemas/errors.py
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    error:   str
    message: str
    detail:  dict | list | None = None


# Use it in route responses= dicts so docs are accurate
error_responses = {
    400: {"model": ErrorDetail, "description": "Bad request"},
    401: {"model": ErrorDetail, "description": "Not authenticated"},
    403: {"model": ErrorDetail, "description": "Insufficient permissions"},
    404: {"model": ErrorDetail, "description": "Resource not found"},
    409: {"model": ErrorDetail, "description": "Resource already exists"},
    422: {"model": ErrorDetail, "description": "Validation failed"},
    500: {"model": ErrorDetail, "description": "Internal server error"},
}