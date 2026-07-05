import hashlib
import secrets

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
    def generate_participant_code(max_id: int) -> str:
        """Generate a unique 10-digit participant code from a Max ID.

        The generation process:
        1. Combines Max ID with a random hex token
        2. Creates an SHA-256 hash of the combined input
        3. Extracts the first 8 bytes of the hash
        4. Converts bytes to an integer and takes modulo 10^10
        5. Formats as a zero-padded 10-digit string

        Args:
            max_id: User's Max ID used as entropy source

        Returns:
            A 10-digit zero-padded string representing the participant code
        """

        hash_input = f"{max_id}{secrets.token_hex(8)}".encode()
        digest = hashlib.sha256(hash_input).digest()
        number = int.from_bytes(digest[:8], byteorder='big')
        participant_id = number % (10 ** 10)
        return f"{participant_id:010d}"

    async def get_by_max_id(self, max_id: int) -> Participant:
        """
        Retrieve a participant by their Max ID.

        Args:
            max_id: User's Max ID

        Returns:
            Participant object if found

        Raises:
            UserNotFoundError: If no participant exists with the given Max ID
        """
        participant = await self._repo.get_by_max_id(max_id)
        if not participant:
            raise UserNotFoundError(max_id)
        return participant

    async def get_group(self, max_id: int) -> str:
        """
        Get the participant's assigned study group.

        Args:
            max_id: User's Max ID

        Returns:
            Group name ('A' or 'B')

        Raises:
            UserNotFoundError: If no participant exists with the given max ID
        """

        group = await self._repo.get_group_by_max_id(max_id)
        if not group:
            raise UserNotFoundError(max_id)
        return group

    async def exists(self, max_id: int) -> bool:
        """
        Check if a participant exists in the system.

        Args:
            max_id: User's max ID to check

        Returns:
            True if participant exists, False otherwise
        """
        return await self._repo.exists(max_id)

    async def save(self, participant: Participant) -> Participant:
        """
        Save a participant to the database.

        Args:
            participant: Participant object to save

        Returns:
            The saved Participant object (may include generated fields)
        """
        return await self._repo.save(participant)

    async def generate_unique_participant_code(self, max_id: int, max_attempts: int = 10) -> str:
        """
        Generate a unique participant code with collision detection.

        Attempts to generate a unique code up to max_attempts times.
        If collisions are detected, regenerates with new random entropy.
        Args:
            max_id: User's Max ID for code generation
            max_attempts: Maximum number of generation attempts before failing

        Returns:
            A unique participant code not existing in the database

        Raises:
            RuntimeError: If unable to generate a unique code after max_attempts
        """
        for _ in range(max_attempts):
            code = self.generate_participant_code(max_id)
            if not await self._repo.exists_by_code(code):
                return code
        raise RuntimeError(f"Не удалось сгенерировать уникальный код после {max_attempts} попыток")
