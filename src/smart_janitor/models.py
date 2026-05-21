import pathlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Extension(BaseModel):
    """Match files by extension (normalized, dot-less, lowercase)."""

    type: Literal["extension"]
    pattern: str

    @field_validator("pattern")
    @classmethod
    def normalize_extension(cls, v: str) -> str:
        """Strip leading dot and lowercase the extension."""
        return v.lstrip(".").lower()


class Regex(BaseModel):
    type: Literal["regex"]
    pattern: str


class Size(BaseModel):
    type: Literal["size"]
    threshold: float
    unit: Literal["B", "KB", "MB", "GB"]
    operator: Literal["lt", "gt", "eq"]


class Age(BaseModel):
    type: Literal["age"]
    older_than_days: int = Field(ge=0)


class MoveTo(BaseModel):
    kind: Literal["move_to"]
    dst: pathlib.Path


class Rename(BaseModel):
    kind: Literal["rename"]
    pattern: str
    replacement: str


class Archive(BaseModel):
    kind: Literal["archive"]
    dst: pathlib.Path


class Rule(BaseModel):
    match: Extension | Regex | Size | Age = Field(discriminator="type")
    action: MoveTo | Rename | Archive = Field(discriminator="kind")


class FileInfo(BaseModel):
    """Metadata describing a file on disk."""

    path: pathlib.Path
    size: int
    mtime: datetime
    extension: str

    @field_validator("extension")
    @classmethod
    def normalize_extension(cls, v: str) -> str:
        """Strip leading dot and lowercase the extension."""
        return v.lstrip(".").lower()


class Move(BaseModel):
    src: pathlib.Path | str
    dst: pathlib.Path | str
    rule: Rule
