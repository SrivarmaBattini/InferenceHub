# exceptions.py
from fastapi import status

class InferenceHubError(Exception):
    """Base exception for all InferenceHub domain errors."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code:  str = "INTERNAL_ERROR"

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)


class NotFoundError(InferenceHubError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "NOT_FOUND"


class ConflictError(InferenceHubError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "CONFLICT"


class UnauthorizedError(InferenceHubError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "UNAUTHORIZED"


class ForbiddenError(InferenceHubError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "FORBIDDEN"


class ValidationError(InferenceHubError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "VALIDATION_ERROR"