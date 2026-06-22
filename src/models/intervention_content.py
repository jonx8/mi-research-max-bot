from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class InterventionContent(Base):
    """Educational and motivational content for Group B (intervention)."""
    __tablename__ = 'intervention_content'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-6
    week: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-24 (weeks from program start)
    content_type: Mapped[str] = mapped_column(String, nullable=False)  # 'educational', 'motivational'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class InterventionContentLog(Base):
    """Log of educational and motivational content delivery."""
    __tablename__ = 'intervention_content_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_code: Mapped[str] = mapped_column(
        String,
        ForeignKey('participants.participant_code', ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('intervention_content.id'),
        nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
