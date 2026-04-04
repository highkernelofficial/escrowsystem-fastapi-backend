from pydantic import BaseModel


class DeployContractRequest(BaseModel):
    sender: str


class GetAppIdRequest(BaseModel):
    txn_id: str


# 🔥 FIXED
class FundProjectRequest(BaseModel):
    sender: str
    app_id: int     # 🔥 instead of escrow_address
    amount: float


class ReleaseMilestoneRequest(BaseModel):
    sender: str
    app_id: int
    milestone_id: str
    freelancer_address: str
    amount: float