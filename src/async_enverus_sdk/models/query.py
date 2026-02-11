"""Query parameter models with validation."""

from pydantic import BaseModel, ConfigDict, Field


class QueryParams(BaseModel):
    """Structural query params with validation. Extra fields pass through as filters."""

    dataset: str
    fields: list[str] | None = None
    pagesize: int = Field(default=10_000, ge=1, le=100_000)
    paging: bool = True
    model_config = ConfigDict(extra="allow")
