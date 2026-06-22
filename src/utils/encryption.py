import base64

from cryptography.hazmat.primitives.ciphers.aead import AESSIV


class EncryptionService:
    """Service for deterministic encryption and decryption of data."""

    def __init__(self, key: str | None = None):
        """
        Initialize the encryption service.

        Args:
            key: Encryption key (base64, 64 bytes for AES-SIV-256).
                If not provided, a new one is generated.
        """
        if key:
            self._key = self._validate_and_normalize_key(key)
        else:
            self._key = self._generate_key_bytes()

        self._cipher = AESSIV(self._key)

    @staticmethod
    def _validate_and_normalize_key(key: str) -> bytes:
        """
        Validate and normalize the encryption key.

        Args:
            key: Key as a base64 string.

        Returns:
            Key in bytes format (64 bytes for AES-SIV-256).

        Raises:
            ValueError: If the key is invalid.
        """
        try:
            # Try to decode from base64
            key_bytes = base64.urlsafe_b64decode(key)

            # Key must be 64 bytes for AES-SIV-256
            if len(key_bytes) != 64:
                raise ValueError(
                    f"Encryption key must be 64 bytes (got {len(key_bytes)}). "
                    "Generate a new key using generate_key()"
                )

            return key_bytes
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")

    @staticmethod
    def _generate_key_bytes() -> bytes:
        """
        Generate a new encryption key (64 bytes for AES-SIV-256).

        Returns:
            Key in bytes format.
        """
        import os
        return os.urandom(64)

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key.

        Returns:
            Key as a base64 string (for saving to .env).
        """
        key_bytes = EncryptionService._generate_key_bytes()
        return base64.urlsafe_b64encode(key_bytes).decode('utf-8')

    def encrypt(self, value: int | str) -> str:
        """
        Encrypts a value deterministically (AES-SIV).
        Identical input data always produces identical encrypted output.

        Args:
            value: Integer or string to encrypt.

        Returns:
            Encrypted string (base64).
        """
        data = str(value).encode('utf-8')
        # AES-SIV does not require a nonce; it is deterministic.
        encrypted = self._cipher.encrypt(data, associated_data=None)
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')

    def decrypt(self, encrypted_value: str) -> str:
        """
        Decrypts a value.

        Args:
            encrypted_value: Encrypted string.

        Returns:
            Decrypted string.

        Raises:
            ValueError: If the token is invalid.
        """
        try:
            data = base64.urlsafe_b64decode(encrypted_value)
            decrypted = self._cipher.decrypt(data, associated_data=None)
            return decrypted.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption error: {e}")

    def decrypt_to_int(self, encrypted_value: str) -> int:
        """
        Decrypts a value and returns it as an integer.

        Args:
            encrypted_value: Encrypted string.

        Returns:
            Decrypted integer.
        """
        return int(self.decrypt(encrypted_value))


# Global instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """
    Get the global encryption service instance.

    Returns:
        EncryptionService instance.

    Raises:
        RuntimeError: If the service is not initialized.
    """
    if _encryption_service is None:
        raise RuntimeError(
            "EncryptionService is not initialized. "
            "Call init_encryption() in main.py"
        )
    return _encryption_service


def init_encryption(encryption_key: str | None = None) -> EncryptionService:
    """
    Initialize the global encryption service.

    Args:
        encryption_key: Encryption key from config.

    Returns:
        EncryptionService instance.
    """
    global _encryption_service
    _encryption_service = EncryptionService(encryption_key)
    return _encryption_service
