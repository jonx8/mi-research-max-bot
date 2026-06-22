from typing import Optional, List

from sqlalchemy import select

from src.database import Database
from src.models import Participant
from src.utils.encryption import get_encryption_service


class ParticipantRepository:
    """Repository for participant data access operations."""

    def __init__(self, db: Database):
        """
        Initialize the repository with a database connection.

        Args:
            db: Database instance providing session management
        """
        self._db = db

    async def save(self, participant: Participant) -> Participant:
        """
        Save or update a participant in the database.

        Args:
            participant: Participant object to persist

        Returns:
            The saved Participant object
        """
        async with self._db.get_db_session() as session:
            session.add(participant)
            await session.flush()
            return participant

    async def get_by_id(self, participant_code: str) -> Optional[Participant]:
        """
        Retrieve a participant by their unique participant code.

        Args:
            participant_code: participant identifier

        Returns:
            Participant object if found, None otherwise
        """
        async with self._db.get_db_session() as session:
            return await session.get_one(Participant, ident=participant_code)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Participant]:
        """
        Retrieve a participant by Telegram ID.

        Automatically encrypts the Telegram ID for database lookup
        to match the stored encrypted value.

        Args:
            telegram_id: User's Telegram ID (plaintext)

        Returns:
            Participant object if found, None otherwise
        """
        encryption_service = get_encryption_service()
        encrypted_id = encryption_service.encrypt(telegram_id)

        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(Participant).where(Participant.telegram_id_encrypted == encrypted_id)
            )
            return result.scalar_one_or_none()

    async def get_group_by_telegram_id(self, telegram_id: int) -> Optional[str]:
        """
        Get only the group name for a participant by Telegram ID.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            Group name ('A' or 'B') if found, None otherwise
        """
        encryption_service = get_encryption_service()
        encrypted_id = encryption_service.encrypt(telegram_id)

        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(Participant.group_name).where(Participant.telegram_id_encrypted == encrypted_id)
            )
            return result.scalar_one_or_none()

    async def exists(self, telegram_id: int) -> bool:
        """
        Check if a participant exists by Telegram ID.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            True if participant exists, False otherwise
        """
        encryption_service = get_encryption_service()
        encrypted_id = encryption_service.encrypt(telegram_id)

        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(Participant.telegram_id_encrypted).where(Participant.telegram_id_encrypted == encrypted_id)
            )
            return result.scalar_one_or_none() is not None

    async def exists_by_code(self, participant_code: str) -> bool:
        """
        Check if a participant exists by participant code.

        Used during code generation to ensure uniqueness.

        Args:
            participant_code: The 10-digit participant code to check

        Returns:
            True if participant with this code exists, False otherwise
        """
        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(Participant.participant_code).where(Participant.participant_code == participant_code)
            )
            return result.scalar_one_or_none() is not None

    async def get_all_by_group(self, group_name: str) -> List[Participant]:
        """
        Retrieve all participants belonging to a specific study group.

        Args:
            group_name: Study group name ('A' or 'B')

        Returns:
            List of Participant objects in the specified group
        """
        async with self._db.get_db_session() as session:
            result = await session.execute(select(Participant).where(Participant.group_name == group_name))
            return result.scalars().all()
