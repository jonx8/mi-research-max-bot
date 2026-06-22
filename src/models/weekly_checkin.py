from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class WeeklyCheckIn(Base):
    """Weekly check-ins (Group B only)."""
    __tablename__ = 'weekly_checkins'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_code: Mapped[str] = mapped_column(
        String,
        ForeignKey('participants.participant_code', ondelete="CASCADE"),
        nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    smoking_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    craving_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class WeeklyCheckInSession(Base):
    """Weekly check-in session model for intermediate data storage."""
    __tablename__ = 'weekly_checkin_sessions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id_encrypted: Mapped[str] = mapped_column(String, nullable=False, index=True)  # Encrypted telegram_id
    checkin_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Intermediate answers
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    craving: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    @property
    def telegram_id(self) -> int:
        """Returns the decrypted telegram_id."""
        from src.utils.encryption import get_encryption_service
        encryption_service = get_encryption_service()
        return encryption_service.decrypt_to_int(self.telegram_id_encrypted)
