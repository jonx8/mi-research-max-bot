from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class MorningTip(Base):
    """Morning tips."""
    __tablename__ = 'morning_tips'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
