
from pydantic import BaseModel
from typing import List


class DeployContractRequest(BaseModel):
    sender: str


class GetAppIdRequest(BaseModel):
    txn_id: str


class MilestoneFundItem(BaseModel):
    milestone_id: str
    amount: float  # in ALGOs


class FundProjectRequest(BaseModel):
    sender: str
    app_id: int
    milestones: List[MilestoneFundItem]   # all milestones for this project
    total_amount: float                    # sum of all milestone amounts (in ALGOs)


class ReleaseMilestoneRequest(BaseModel):
    sender: str
    app_id: int
    milestone_id: str
    freelancer_address: str