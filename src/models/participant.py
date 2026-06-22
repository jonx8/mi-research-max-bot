from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.encryption import get_encryption_service


class Participant(Base):
    """Main participant information."""
    __tablename__ = 'participants'

    participant_code: Mapped[str] = mapped_column(primary_key=True)
    telegram_id_encrypted: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )
    group_name: Mapped[str] = mapped_column(nullable=False)
    registration_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
    age: Mapped[int] = mapped_column(nullable=False)
    gender: Mapped[str] = mapped_column(nullable=False)
    clinic_center: Mapped[str] = mapped_column(nullable=False)

    @property
    def telegram_id(self) -> int:
        encryption_service = get_encryption_service()
        return encryption_service.decrypt_to_int(
            self.telegram_id_encrypted
        )
