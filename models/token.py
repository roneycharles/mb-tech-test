from datetime import datetime

from sqlalchemy.sql.functions import func
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import String, BigInteger, Boolean, Integer, DateTime, Enum as SQLEnum

from constants.tokens import TokenType
from core.database import Base


class Token(Base):
    __tablename__ = "tokens"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    name: str = Column(String, nullable=False)
    symbol: str = Column(String, nullable=False)
    address: str = Column(String, unique=True, index=True, nullable=False)
    decimals: int = Column(Integer, nullable=False)
    is_active: bool = Column(Boolean, nullable=False, default=True)
    type: str = Column(SQLEnum(TokenType), nullable=False)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


    def __repr__(self) -> str:
        return f"<Token(id={self.id}, symbol='{self.address}, is_active={self.is_active})>"