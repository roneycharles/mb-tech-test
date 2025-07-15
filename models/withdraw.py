from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime, Enum as SQLEnum, text, Index, CheckConstraint
from sqlalchemy.sql.functions import func
from sqlalchemy.sql.sqltypes import Numeric

from constants.withdraw import WithdrawStatus
from core.database import Base


class Withdraw(Base):
    __tablename__ = 'withdrawals'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tx_hash: str = Column(String, nullable=True, index=True)
    status: str = Column(SQLEnum(WithdrawStatus), nullable=False, default=WithdrawStatus.PENDING)
    address_id: int = Column(BigInteger, ForeignKey('addresses.id'), nullable=False)
    to_address: str = Column(String, nullable=False)
    token_id: int = Column(BigInteger, ForeignKey('tokens.id'), nullable=False)
    amount: Decimal = Column(Numeric(precision=36, scale=18), nullable=False)
    confirmations: int = Column(BigInteger, nullable=False, default=0)
    gas_cost: Decimal = Column(Numeric(precision=36, scale=18), nullable=False, default=0)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            'ix_withdraws_tx_hash_unique',
            'tx_hash',
            unique=True,
            postgresql_where=text('tx_hash IS NOT NULL'),

        ),
        CheckConstraint(
            """
            (status IN ('PENDING', 'FAILED') AND tx_hash IS NULL) OR
            (status NOT IN ('PENDING', 'FAILED') AND tx_hash IS NOT NULL)
            """,
            name='check_tx_hash_status_consistency'
        )
    )

    def __repr__(self) -> str:
        return f"<Withdraw(id={self.id}, tx_hash='{self.tx_hash}', status={self.status})>"