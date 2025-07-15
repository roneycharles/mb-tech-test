from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, ConfigDict


class CreateAddressesRequest(BaseModel):
    quantity: int = Field(..., gt=0, description="The quantity of items to create.")

class CreateAddressesResponse(BaseModel):
    status: str = "success"
    total_created: int
    message: str

class Address(BaseModel):
    address: str
    is_active: bool

class AddressInDB(Address):
    id: int = Field(..., description="Address id")
    # private_key: str = Field(..., description="Private key of address", exclude=True)
    created_at: datetime = Field(..., description="Deposit creation time")

    model_config = ConfigDict(from_attributes=True)

# class AddressInResponse(BaseModel):
#     id: int = Field(..., description="Address id")
#     address: str = Field(..., description="Wallet address")
#     is_active: bool = Field(..., description="Address activation status")
#     created_at: datetime = Field(..., description="Address creation time")

class ListAddressesResponse(BaseModel):
    addresses: List[AddressInDB] = Field(..., description="List of addresses")
    total: int = Field(..., description="Total number of addresses")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Total number of addresses per page")
    message: str = Field(..., description="Request status message")

class GetAddressRequest(BaseModel):
    address: str = Field(..., description="The address to search on database.")

class GetAddressResponse(BaseModel):
    address: Address