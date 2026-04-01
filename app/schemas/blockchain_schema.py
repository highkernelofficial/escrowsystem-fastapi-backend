from pydantic import BaseModel

class TxnRequest(BaseModel):
    sender: str
    receiver: str
    amount: int