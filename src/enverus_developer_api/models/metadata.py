"""Dataset metadata models (DDL, docs)."""

from pydantic import BaseModel


class DDLField(BaseModel):
    """A single field from a DDL statement."""

    name: str
    type: str
    primary_key: bool = False


class DocsField(BaseModel):
    """A single field from the docs endpoint."""

    name: str
    required: bool
    default: str
    requirements: str
    description: str
    filter_type: str
