"""Agent schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class AgentBase(BaseModel):
    """Base agent schema with common fields."""
    token: str = Field(..., min_length=1, max_length=255, description="Agent token/embedding ID")
    endpoint: str = Field(..., min_length=1, max_length=255, description="API endpoint URL")
    environment: str = Field(default="local", min_length=1, max_length=100, description="Environment (local, production, etc.)")
    js_source: str = Field(..., min_length=1, max_length=500, description="JavaScript source URL")
    script: str = Field(..., min_length=1, max_length=100, description="Script identifier")
    category: str = Field(..., min_length=1, max_length=100, description="Agent category")
    language: str = Field(..., min_length=1, max_length=20, description="Agent language code")
    name: str = Field(..., min_length=1, max_length=255, description="Agent display name")
    finger_hole: Optional[str] = Field(None, max_length=255, description="Image path for finger hole")
    scrollable_agent_card: Optional[str] = Field(None, max_length=255, description="Image path for scrollable card")
    info: Optional[str] = Field(None, description="Agent description/info")


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""
    is_active: bool = Field(default=True, description="Whether agent is active")


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""
    token: Optional[str] = Field(None, min_length=1, max_length=255)
    endpoint: Optional[str] = Field(None, min_length=1, max_length=255)
    environment: Optional[str] = Field(None, min_length=1, max_length=100)
    js_source: Optional[str] = Field(None, min_length=1, max_length=500)
    script: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    language: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    finger_hole: Optional[str] = Field(None, max_length=255)
    scrollable_agent_card: Optional[str] = Field(None, max_length=255)
    info: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)


class AgentStatusUpdate(BaseModel):
    """Schema for updating only agent status."""
    is_active: bool = Field(..., description="Agent active status")


class AgentResponse(AgentBase):
    """Schema for agent response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    """Schema for paginated agent list response."""
    items: List[AgentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AgentExport(BaseModel):
    """Schema for agent export (JSON/CSV)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    token: str
    endpoint: str
    environment: str
    js_source: str
    script: str
    category: str
    language: str
    name: str
    finger_hole: Optional[str] = None
    scrollable_agent_card: Optional[str] = None
    info: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
