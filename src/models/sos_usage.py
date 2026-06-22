from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class SOSUsage(Base):
    """SOS button usage tracking."""
    __tablename__ = 'sos_usage'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_code: Mapped[str] = mapped_column(
        String,
        ForeignKey('participants.participant_code', ondelete="CASCADE"),
        nullable=False
    )
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    technique_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey('techniques.id'),
        nullable=True
    )
