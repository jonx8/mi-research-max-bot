import hashlib
import secrets

from telegram import ReplyKeyboardMarkup, KeyboardButton

from src.exceptions import UserNotFoundError

from src.models import Participant
from src.repositories import ParticipantRepository


class ParticipantService:
    """Service layer for participant business logic."""

    def __init__(self, repo: ParticipantRepository):
        """
        Initialize the participant service with a repository instance.

        Args:
            repo: Repository instance for participant data access operations
        """
        self._repo = repo

    @staticmethod
    def generate_participant_code(telegram_id: int) -> str:
        """Generate a unique 10-digit participant code from a Telegram ID.

        The generation process:
        1. Combines Telegram ID with a random hex token
        2. Creates an SHA-256 hash of the combined input
        3. Extracts the first 8 bytes of the hash
        4. Converts bytes to an integer and takes modulo 10^10
        5. Formats as a zero-padded 10-digit string

        Args:
            telegram_id: User's Telegram ID used as entropy source

        Returns:
            A 10-digit zero-padded string representing the participant code
        """

        hash_input = f"{telegram_id}{secrets.token_hex(8)}".encode()
        digest = hashlib.sha256(hash_input).digest()
        number = int.from_bytes(digest[:8], byteorder='big')
        participant_id = number % (10 ** 10)
        return f"{participant_id:010d}"

    async def get_by_telegram_id(self, telegram_id: int) -> Participant:
        """
        Retrieve a participant by their Telegram ID.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            Participant object if found

        Raises:
            UserNotFoundError: If no participant exists with the given Telegram ID
        """
        participant = await self._repo.get_by_telegram_id(telegram_id)
        if not participant:
            raise UserNotFoundError(telegram_id)
        return participant

    async def get_main_keyboard(self, telegram_id: int):
        """
        Generate the main keyboard layout based on participant status and group.

        Returns different keyboard configurations:
        - Empty keyboard: User not registered yet
        - Group B keyboard: Includes SOS emergency help button
        - Group A keyboard: Standard keyboard without SOS button

        Args:
            telegram_id: User's Telegram ID

        Returns:
            ReplyKeyboardMarkup configured for the user's current state
        """
        if not await self.exists(telegram_id):
            return ReplyKeyboardMarkup([[]], resize_keyboard=True)

        user_group = await self.get_group(telegram_id)

        if user_group == 'B':
            return ReplyKeyboardMarkup([
                [KeyboardButton("🆘 SOS - Экстренная помощь")],
                [KeyboardButton("ℹ️ Мой код участника")],
                [KeyboardButton("ℹ️ Помощь")]
            ], resize_keyboard=True)
        else:
            return ReplyKeyboardMarkup([
                [KeyboardButton("ℹ️ Мой код участника")],
                [KeyboardButton("ℹ️ Помощь")]
            ], resize_keyboard=True)

    async def get_group(self, telegram_id: int) -> str:
        """
        Get the participant's assigned study group.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            Group name ('A' or 'B')

        Raises:
            UserNotFoundError: If no participant exists with the given Telegram ID
        """

        group = await self._repo.get_group_by_telegram_id(telegram_id)
        if not group:
            raise UserNotFoundError(telegram_id)
        return group

    async def exists(self, telegram_id: int) -> bool:
        """
        Check if a participant exists in the system.

        Args:
            telegram_id: User's Telegram ID to check

        Returns:
            True if participant exists, False otherwise
        """
        return await self._repo.exists(telegram_id)

    async def save(self, participant: Participant) -> Participant:
        """
        Save a participant to the database.

        Args:
            participant: Participant object to save

        Returns:
            The saved Participant object (may include generated fields)
        """
        return await self._repo.save(participant)

    async def generate_unique_participant_code(self, telegram_id: int, max_attempts: int = 10) -> str:
        """
        Generate a unique participant code with collision detection.

        Attempts to generate a unique code up to max_attempts times.
        If collisions are detected, regenerates with new random entropy.
        Args:
            telegram_id: User's Telegram ID for code generation
            max_attempts: Maximum number of generation attempts before failing

        Returns:
            A unique participant code not existing in the database

        Raises:
            RuntimeError: If unable to generate a unique code after max_attempts
        """
        for _ in range(max_attempts):
            code = self.generate_participant_code(telegram_id)
            if not await self._repo.exists_by_code(code):
                return code
        raise RuntimeError(f"Не удалось сгенерировать уникальный код после {max_attempts} попыток")
