from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class DailyLog(Base):
    """Daily activity (Group B only)."""
    __tablename__ = 'daily_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_code: Mapped[str] = mapped_column(
        String,
        ForeignKey('participants.participant_code', ondelete="CASCADE"),
        nullable=False
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)

    morning_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    high_dep_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    evening_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    evening_response: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # ✅ Да / ❌ Трудности / 🆘 Тяга
    evening_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)