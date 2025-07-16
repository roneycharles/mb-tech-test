import os
from unittest.mock import Mock

import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    test_env_vars = {
        'DB_NAME': 'test_database',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_password',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'MAINNET_RPC_URL': 'http://localhost:8545',
        'TESTNET_RPC_URL': 'http://localhost:8545',
        'CHAIN_ID': '1337',
        'USDC_CONTRACT': '0x1234567890123456789012345678901234567890',
        'USDT_CONTRACT': '0x0987654321098765432109876543210987654321',
        'ENCRYPTION_KEY': 'test_encryption_key_32_chars_long',
        'ENVIRONMENT': 'test'
    }

    original_values = {}
    for key in test_env_vars.keys():
        if key in os.environ:
            original_values[key] = os.environ[key]

    for key, value in test_env_vars.items():
        os.environ[key] = value

    yield

    for key in test_env_vars.keys():
        if key in original_values:
            os.environ[key] = original_values[key]
        else:
            os.environ.pop(key, None)

@pytest.fixture()
def mock_security_manager():
    mock = Mock()
    mock.generate_account.return_value = ("0xAddress", "private_key")
    mock.encrypt_private_key.return_value = "encrypted_private_key"
    mock.decrypt_private_key.return_value = "decrypted_private_key"
    return mock

@pytest.fixture()
def mock_db_session():
    from unittest.mock import AsyncMock
    from sqlalchemy.ext.asyncio import AsyncSession
    return AsyncMock(spec=AsyncSession)