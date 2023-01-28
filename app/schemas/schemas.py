from typing import Optional, Union, List, Dict
from pydantic import BaseModel, Field

erd_address_format = "erd..."


class Bet(BaseModel):
    walletAddress: str = Field(None, title=erd_address_format, min_length=62, max_length=62)
    betAmount: float = Field(None, title="Bet Amount in EGLD")


class CashoutAddress(BaseModel):
    walletAddress: str = Field(None, title=erd_address_format)


class User(BaseModel):
    walletAddress: str = Field(None, title=erd_address_format, min_length=62, max_length=62)
    balance: Optional[float] = Field(None, title="The amount of EGLD available")
    signer: Optional[str] = Field(None, title="The signer of the user")


class Response(BaseModel):
    path: str = Field(None, title="name of the called endpoint")
    response: Union[List, str, float, bool, Dict] = Field(
        None, title="The Response of the endpoint"
    )
