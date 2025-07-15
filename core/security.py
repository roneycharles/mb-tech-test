import logging

from cryptography.fernet import Fernet
from eth_account import Account
from eth_utils import to_checksum_address

from core.config import settings

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self):
        encryption_key = settings.ENCRYPTION_KEY
        self.cipher_suite = Fernet(encryption_key.encode())

    def encrypt_private_key(self, private_key: str) -> str:
        try:
            if not private_key:
                raise Exception("private_key cannot be empty")
            encrypted = self.cipher_suite.encrypt(private_key.encode())

            return encrypted.decode()
        except Exception as e:
            logger.error("Failed to encrypt private key: %s", e)
            raise

    def decrypt_private_key(self, private_key: str) -> str:
        try:
            if not private_key:
                raise Exception("private_key cannot be empty")
            decrypted = self.cipher_suite.decrypt(private_key.encode())

            return decrypted.decode()
        except Exception as e:
            logger.error("Failed to decrypt private key: %s", e)
            raise

    @staticmethod
    def generate_account() -> tuple[str, str]:
        try:
            account = Account.create()
            address = to_checksum_address(account.address)
            private_key = account.key.hex()

            return address, private_key
        except Exception as e:
            logger.error("Failed to generate account: %s", e)
            raise

def get_security_manager() -> SecurityManager:
    return SecurityManager()