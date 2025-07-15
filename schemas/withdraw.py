from datetime import datetime
from decimal import Decimal
from typing import List, Self, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator, field_serializer

from constants.withdraw import WithdrawStatus

class TransferInfo(BaseModel):
    token: str
    from_address: str
    to_address: str
    amount: Decimal

class Withdraw(BaseModel):
    status: WithdrawStatus = Field(..., description="Transaction status")
    address_id: int = Field(..., description="Owner address id")
    to_address: str = Field(..., description="Receiver address")
    token_id: int = Field(..., description="Token id to transfer")
    amount: Decimal = Field(..., description="Withdraw amount")

class WithdrawInDB(Withdraw):
    id: int = Field(..., description="Withdraw id")
    tx_hash: Optional[str] = Field(..., description="Transaction hash")
    gas_cost: Optional[Decimal] = Field(..., description="Transaction gas cost")
    confirmations: int = Field(..., description="Number of transaction confirmations")
    created_at: datetime = Field(..., description="Withdraw creation time")

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('gas_cost')
    def serialize_gas_cost(self, value: Optional[Decimal]) -> Optional[str]:
        if value is None:
            return None
        if value == 0:
            return "0"
        return f"{value:.18f}".rstrip('0').rstrip('.')

class CreateWithdrawRequest(BaseModel):
    from_address: str = Field(..., description="From address")
    to_address: str = Field(..., description="Destination address")
    symbol: str = Field(..., description="Token symbol to be transferred")
    amount: Decimal = Field(..., gt=0, description="Amount to transfer")


    @field_validator("from_address", "to_address")
    @classmethod
    def validate_address(cls, v) -> str:
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid address format")
        return v.lower()

    @model_validator(mode='after')
    def validate_different_addresses(self) -> Self:
        if self.from_address == self.to_address:
            raise ValueError("The addresses cannot be the same")
        return self

class CreateWithdrawResponse(BaseModel):
    withdraw: WithdrawInDB
    message: str

class ListWithdrawalsResponse(BaseModel):
    withdrawals: List[WithdrawInDB]
    total: int
    page: int
    page_size: int
    message: str

class UpdateWithdrawRequest(BaseModel):
    tx_hash: str = Field(..., description="Transaction hash")

class UpdateWithdrawResponse(BaseModel):
    tx_hash: str
    withdraw: WithdrawInDB
    status: str
    message: str
