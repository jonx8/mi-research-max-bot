from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class Technique(Base):
    """Techniques for craving management."""
    __tablename__ = 'techniques'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
