"""Agent model for agent hotline management."""
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlalchemy import String, Text, DateTime, Boolean, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class AgentMode(str, Enum):
    TEXT = "text"
    VOICE = "voice"


class Agent(Base):
    """Agent configuration managed by Agent Hotline."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    environment: Mapped[str] = mapped_column(String(100), nullable=False, default="local")
    js_source: Mapped[str] = mapped_column(String(500), nullable=False)
    script: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    finger_hole: Mapped[str] = mapped_column(String(255), nullable=True)
    scrollable_agent_card: Mapped[str] = mapped_column(String(255), nullable=True)
    info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="text", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_agents_name", "name"),
        Index("ix_agents_category", "category"),
        Index("ix_agents_language", "language"),
        Index("ix_agents_active", "is_active"),
        Index("ix_agents_active_created", "is_active", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', active={self.is_active})>"
