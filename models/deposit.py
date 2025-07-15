from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.sql.functions import func
from sqlalchemy.sql.sqltypes import Numeric

from constants.deposit import DepositStatus
from core.database import Base


class Deposit(Base):
    __tablename__ = 'deposits'

    __table_args__ = (
        # TODO: Validate this constraint: test with transactions sender from some exchanges
        #  smart contracts(coinbase, binance, kucoin),in some cases, the same hash can carry
        #  multiple transactions to the same address or to more than one address in our database.
        # PrimaryKeyConstraint("tx_hash", "address_id", "token_id",  name="pkey_hash_addr_token"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # TODO: Change unique to False when validate and activate PrimaryKeyConstraint
    tx_hash: str = Column(String, unique=True, index=True, nullable=False)
    status: str = Column(SQLEnum(DepositStatus), nullable=False, default=DepositStatus.PENDING)
    address_id: int = Column(BigInteger, ForeignKey('addresses.id'), nullable=False)
    from_address: str = Column(String, nullable=False)
    token_id: int = Column(BigInteger, ForeignKey('tokens.id'), nullable=False)
    amount: Decimal = Column(Numeric(precision=36, scale=18), nullable=False)
    confirmations: int = Column(BigInteger, nullable=False, default=0)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Deposit(id={self.id}, tx_hash='{self.tx_hash}', status={self.status})>"