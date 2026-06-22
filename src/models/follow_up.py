from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class FollowUp(Base):
    """Intermediate surveys (1 and 3 months)."""
    __tablename__ = 'follow_ups'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_code: Mapped[str] = mapped_column(
        String,
        ForeignKey('participants.participant_code', ondelete="CASCADE"),
        nullable=False
    )
    scheduled_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    ppa_7d: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    cigs_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class FollowUpSession(Base):
    """Follow-up survey session model for intermediate data storage."""
    __tablename__ = 'follow_up_sessions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id_encrypted: Mapped[str] = mapped_column(String, nullable=False, index=True)  # Encrypted telegram_id
    follow_up_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    ppa_7d: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    @property
    def telegram_id(self) -> int:
        """Returns the decrypted telegram_id."""
        from src.utils.encryption import get_encryption_service
        encryption_service = get_encryption_service()
        return encryption_service.decrypt_to_int(self.telegram_id_encrypted)
