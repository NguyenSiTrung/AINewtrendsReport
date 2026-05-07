"""ORM model for the SettingsKV table."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ainews.models.base import Base


class SettingsKV(Base):
    """Key-value store for application settings (e.g., ``smtp.host``)."""

    __tablename__ = "settings_kv"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[str | None] = mapped_column(String, nullable=True)
