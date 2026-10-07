"""Settings schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SettingBase(BaseModel):
    """Base setting schema."""
    key: str = Field(..., min_length=1, max_length=100, description="Setting key")
    value: str = Field(..., description="Setting value")
    description: Optional[str] = Field(None, max_length=255, description="Setting description")


class SettingResponse(SettingBase):
    """Schema for setting response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class SettingUpdate(BaseModel):
    """Schema for updating settings."""
    value: str = Field(..., description="New setting value")
    description: Optional[str] = Field(None, max_length=255, description="Setting description")


class WebhookUrlResponse(BaseModel):
    """Schema for webhook URL response."""
    webhook_url: str = Field(..., description="Full webhook URL")
    host: str = Field(..., description="Configured host")
    port: int = Field(..., description="Configured port")
    path: str = Field(..., description="Configured path")