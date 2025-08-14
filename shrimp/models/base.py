"""Base models and common types."""

from typing import Any
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic models."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class DocumentBase(BaseModel):
    """Base model for MongoDB documents."""
    
    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        validate_by_name=True,
        use_enum_values=True
    )