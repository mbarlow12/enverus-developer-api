"""Error response model."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Structured error response from the API."""

    status_code: int
    message: str
    detail: str = ""
