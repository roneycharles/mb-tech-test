import logging
from decimal import Decimal
from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, model_validator, ValidationError
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker


class NetworkType(str, Enum):
    MAINNET = "MAINNET"
    TESTNET = "TESTNET"

    def __str__(self):
        return self.value

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def __str__(self):
        return self.value


class Settings(BaseSettings):
    SERVER_HOST: str = Field("0.0.0.0", validation_alias="SERVER_HOST")
    SERVER_PORT: int = Field(3000, validation_alias="SERVER_PORT")

    # DB
    DB_HOST: str = Field("localhost", validation_alias="DB_HOST")
    DB_PORT: str = Field("5432", validation_alias="DB_PORT")
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_URL: Optional[str] = None

    # Web3
    NETWORK_TYPE: NetworkType = Field(NetworkType.MAINNET, validation_alias="NETWORK_TYPE")
    MAINNET_RPC_URL: str
    TESTNET_RPC_URL: str
    RPC_URL: Optional[str] = None

    # Blockchain
    CHAIN_ID: int
    MIN_CONFIRMATIONS: int = Field(1, validation_alias="MIN_CONFIRMATIONS")
    USDC_CONTRACT: str
    USDT_CONTRACT: str

    # Logger
    LOG_LEVEL: LogLevel = Field(LogLevel.INFO, validation_alias="LOG_LEVEL")

    # Security
    ENCRYPTION_KEY: str

    # Transaction
    GAS_PRICE_MULTIPLIER: Decimal = Field(1.2, validation_alias="GAS_PRICE_MULTIPLIER")
    GAS_LIMIT_MULTIPLIER: Decimal = Field(1.1, validation_alias="GAS_LIMIT_MULTIPLIER")
    GAS_PRICE: int = Field(20000000000, validation_alias="GAS_PRICE")
    ETH_GAS_LIMIT: int = Field(21000, validation_alias="ETH_GAS_LIMIT")
    ERC20_GAS_LIMIT: int = Field(65000, validation_alias="ERC20_GAS_LIMIT")

    @model_validator(mode='after')
    def config_db_url(self) -> 'Settings':
        if self.DB_URL:
            return self

        if not all([self.DB_HOST, self.DB_PORT, self.DB_NAME, self.DB_USER, self.DB_PASSWORD]):
            raise ValueError("One or more db required envs are not found in .env")

        db_url = f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        self.DB_URL = db_url.replace("postgresql://", "postgresql+asyncpg://")
        return self

    @model_validator(mode='after')
    def config_web3_url(self) -> 'Settings':
        if self.RPC_URL:
            return self

        if self.NETWORK_TYPE == NetworkType.MAINNET:
            if not self.MAINNET_RPC_URL:
                raise ValueError("MAINNET_RPC_URL env is not found in .env")
            self.RPC_URL = self.MAINNET_RPC_URL
        elif self.NETWORK_TYPE == NetworkType.TESTNET:
            if not self.TESTNET_RPC_URL:
                raise ValueError("TESTNET_RPC_URL env is not found in .env")
            self.RPC_URL = self.TESTNET_RPC_URL
        return self

    class Config:
        env_file = ".env"
        case_sensitive = False

engine: Optional[AsyncEngine] = None
SessionLocal: Optional[sessionmaker[AsyncSession]] = None

@lru_cache()
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        logging.critical(f"Failed to load application settings from .env: {e}")
        raise

settings = get_settings()