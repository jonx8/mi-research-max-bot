from datetime import datetime
from typing import Optional, Dict

from sqlalchemy import Integer, String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class BaselineQuestionnaire(Base):
    """Baseline questionnaire (day 0)."""
    __tablename__ = 'baseline_questionnaires'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_code: Mapped[str] = mapped_column(
        String,
        ForeignKey('participants.participant_code', ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Smoking profile
    smoking_years: Mapped[int] = mapped_column(Integer, nullable=False)
    cigs_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    quit_attempts_before: Mapped[bool] = mapped_column(Boolean, nullable=False)
    uses_vape: Mapped[bool] = mapped_column(Boolean, nullable=False)
    smoker_in_household: Mapped[bool] = mapped_column(Boolean, nullable=False)
    prior_medical_help: Mapped[str] = mapped_column(String, nullable=False)

    # Questionnaires
    fagerstrom_score: Mapped[int] = mapped_column(Integer, nullable=False)
    fagerstrom_level: Mapped[str] = mapped_column(String, nullable=False)
    fagerstrom_1: Mapped[int] = mapped_column(Integer, nullable=False)
    fagerstrom_2: Mapped[int] = mapped_column(Integer, nullable=False)
    fagerstrom_3: Mapped[int] = mapped_column(Integer, nullable=False)
    fagerstrom_4: Mapped[int] = mapped_column(Integer, nullable=False)
    fagerstrom_5: Mapped[int] = mapped_column(Integer, nullable=False)
    fagerstrom_6: Mapped[int] = mapped_column(Integer, nullable=False)

    prochaska_score: Mapped[int] = mapped_column(Integer, nullable=False)
    prochaska_level: Mapped[str] = mapped_column(String, nullable=False)
    prochaska_1: Mapped[int] = mapped_column(Integer, nullable=False)
    prochaska_2: Mapped[int] = mapped_column(Integer, nullable=False)


class RegistrationSession(Base):
    """Registration session model for database storage."""
    __tablename__ = 'registration_sessions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id_encrypted: Mapped[str] = mapped_column(String, unique=True)  # Encrypted telegram_id
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    step: Mapped[str] = mapped_column(String, nullable=False, default='age')

    # Demographics
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    clinic_center: Mapped[str] = mapped_column(String, nullable=True)

    # Smoking profile
    smoking_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cigs_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quit_attempts_before: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    uses_vape: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    smoker_in_household: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    prior_medical_help: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Questionnaires - answers stored as JSON
    fagerstrom_answers: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True, default=dict)
    prochaska_answers: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True, default=dict)

    fagerstrom_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fagerstrom_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prochaska_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prochaska_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    last_bot_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_questionnaire: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    current_question_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    @property
    def telegram_id(self) -> int:
        """Returns the decrypted telegram_id."""
        from src.utils.encryption import get_encryption_service
        encryption_service = get_encryption_service()
        return encryption_service.decrypt_to_int(self.telegram_id_encrypted)
