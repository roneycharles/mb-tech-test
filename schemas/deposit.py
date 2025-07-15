from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field, field_validator, ConfigDict

from constants.deposit import DepositStatus

class CreateDepositRequest(BaseModel):
    tx_hash: str = Field(..., description="Transaction hash to compute deposit")

    @field_validator("tx_hash")
    def validate_tx_hash(cls, value):
        if not value.startswith("0x") or len(value) != 66:
            raise ValueError("Invalid transaction hash format")
        return value.lower()

class Deposit(BaseModel):
    tx_hash: str = Field(..., description="Transaction hash")
    status: DepositStatus = Field(..., description="Transaction status")
    address_id: int = Field(..., description="Owner address id")
    from_address: str = Field(..., description="Sender address")
    token_id: int = Field(..., description="Token to receive")
    amount: Decimal = Field(..., description="Deposit amount")
    confirmations: int = Field(..., description="Number of transaction confirmations")

class DepositInDB(Deposit):
    id: int = Field(..., description="Deposit id")
    created_at: datetime = Field(..., description="Deposit creation time")

    model_config = ConfigDict(from_attributes=True)

class CreateDepositResponse(BaseModel):
    tx_hash: str
    is_valid: bool
    deposits: List[DepositInDB]
    message: str

class ListDepositsResponse(BaseModel):
    deposits: List[DepositInDB]
    total: int
    page: int
    page_size: int
    message: str