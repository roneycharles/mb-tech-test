import logging
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.expression import select

from schemas.token import Token
from models.token import Token as DBToken

logger = logging.getLogger(__name__)

class TokenService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_token_by_symbol(self, symbol: str, is_active: Optional[bool] = None) -> Token:
        try:
            query = select(DBToken).where(DBToken.symbol == symbol.upper())

            if is_active is not None:
                query = query.where(DBToken.is_active == is_active)

            result = await self.db.execute(query)
            token_db = result.scalar()
            if not token_db:
                raise ValueError(f"Token not found with symbol: {symbol}")

            logger.info("Retrieved token by symbol: %s", symbol)
            return Token.model_validate(token_db)
        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error("Database error getting token by symbol %s: %s", symbol, e)
            raise
        except Exception as e:
            logger.error("Unexpected error getting token by symbol %s: %s", symbol, e)
            raise

    async def get_token_by_address(self, address: str, is_active: Optional[bool] = None) -> Token:
        try:
            query = select(DBToken).where(DBToken.address == address.lower())

            if is_active is not None:
                query = query.where(DBToken.is_active == is_active)

            result = await self.db.execute(query)
            token_db = result.scalar()
            if not token_db:
                raise ValueError(f"Token not found with address: {address}")

            logger.info("Retrieved token by address: %s", address)
            return Token.model_validate(token_db)

        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error("Database error getting token by address %s: %s", address, e)
            raise
        except Exception as e:
            logger.error("Unexpected error getting token by address %s: %s", address, e)
            raise

    async def get_token_id_by_symbol(self, symbol: str, is_active: Optional[bool] = None) -> int:
        try:
            query = select(DBToken.id).where(DBToken.symbol == symbol.upper())

            if is_active is not None:
                query = query.where(DBToken.is_active.is_(is_active))

            result = await self.db.execute(query)
            token_id = result.scalar()
            if not token_id:
                raise ValueError(f"Token id not found for symbol: {symbol}")

            logger.info("Retrieved token id %d for symbol: %s", token_id, symbol)
            return token_id

        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error("Database error getting token id by symbol %s: %s", symbol, e)
            raise
        except Exception as e:
            logger.error("Unexpected error getting token id by symbol %s: %s", symbol, e)
            raise

    async def get_token_by_id(self, token_id: int, is_active: Optional[bool] = None) -> Token:
        try:
            query = select(DBToken).where(DBToken.id == token_id)

            if is_active is not None:
                query = query.where(DBToken.is_active.is_(is_active))

            result = await self.db.execute(query)
            token_db = result.scalar()
            if not token_db:
                raise ValueError(f"Token not found with id: {token_id}")

            logger.info("Retrieved token by id: %d", token_id)
            return Token.model_validate(token_db)

        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error("Database error getting token by id %d: %s", token_id, e)
            raise
        except Exception as e:
            logger.error("Unexpected error getting token by id %d: %s", token_id, e)
            raise