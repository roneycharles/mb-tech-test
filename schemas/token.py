from pydantic import BaseModel, ConfigDict

from constants.tokens import TokenType


class Token(BaseModel):
    id: int
    name: str
    symbol: str
    address: str
    decimals: int
    is_active: bool
    type: TokenType

    model_config = ConfigDict(from_attributes=True)