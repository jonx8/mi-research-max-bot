from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class FinalSurvey(Base):
    """Final survey (6 months)."""
    __tablename__ = 'final_surveys'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_code: Mapped[str] = mapped_column(
        String,
        ForeignKey('participants.participant_code', ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    scheduled_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    ppa_30d: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ppa_7d: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    cigs_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quit_attempt_made: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    days_to_first_lapse: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class FinalSurveySession(Base):
    """Final survey session model for intermediate data storage."""
    __tablename__ = 'final_survey_sessions'

    survey_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id_encrypted: Mapped[str] = mapped_column(String, unique=True)  # Encrypted telegram_id
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Intermediate answers
    ppa_30d: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ppa_7d: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    cigs_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quit_attempt_made: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    days_to_first_lapse: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    @property
    def telegram_id(self) -> int:
        """Returns the decrypted telegram_id."""
        from src.utils.encryption import get_encryption_service
        encryption_service = get_encryption_service()
        return encryption_service.decrypt_to_int(self.telegram_id_encrypted)
