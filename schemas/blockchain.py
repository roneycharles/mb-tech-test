from decimal import Decimal

from pydantic import BaseModel

class TransferInfo(BaseModel):
    token_id: int
    from_address: str
    to_address: str
    amount: Decimal