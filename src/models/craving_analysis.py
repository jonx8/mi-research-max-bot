from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class CravingAnalysis(Base):
    """Craving analysis results."""
    __tablename__ = 'craving_analyses'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_code: Mapped[str] = mapped_column(
        String,
        ForeignKey('participants.participant_code', ondelete="CASCADE"),
        nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Responses
    trigger_situation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thoughts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    physical_sensation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coping_strategy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CravingAnalysisSession(Base):
    """Craving analysis session model for database storage."""
    __tablename__ = 'craving_analysis_sessions'

    telegram_id_encrypted: Mapped[str] = mapped_column(String, primary_key=True)  # Encrypted telegram_id
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answers: Mapped[Optional[List]] = mapped_column(JSON, nullable=True, default=list)

    @property
    def telegram_id(self) -> int:
        """Returns the decrypted telegram_id."""
        from src.utils.encryption import get_encryption_service
        encryption_service = get_encryption_service()
        return encryption_service.decrypt_to_int(self.telegram_id_encrypted)
