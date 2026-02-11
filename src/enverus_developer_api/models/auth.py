"""Authentication request/response models."""

from pydantic import BaseModel, ConfigDict, Field


class TokenRequest(BaseModel):
    """Token acquisition request payload for v3 API."""

    secret_key: str = Field(alias="secretKey")
    model_config = ConfigDict(populate_by_name=True)


class TokenResponse(BaseModel):
    """Token acquisition response from v3 API."""

    token: str
