import datetime

from sqlalchemy import Column, BigInteger, String, DateTime, Boolean
from sqlalchemy.sql.functions import func

from core.database import Base

class Address(Base):
    __tablename__: str = "addresses"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    address: str = Column(String, unique=True, index=True, nullable=False)
    private_key: str = Column(String, unique=True, nullable=False)
    is_active: bool = Column(Boolean, nullable=False, default=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Address(id={self.id}, address='{self.address}', is_active={self.is_active})>"