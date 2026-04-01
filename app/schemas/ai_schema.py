from pydantic import BaseModel, Field
from typing import List


class GenerateRequest(BaseModel):
    title: str
    description: str
    tech_stack: List[str]
    expected_outcome: str
    total_budget: float


class EvaluateRequest(BaseModel):
    requirement: str
    submission: str


class Milestone(BaseModel):
    title: str
    description: str
    percentage: float = Field(..., ge=0, le=100)
    amount: float


class GenerateMilestoneResponse(BaseModel):
    milestones: List[Milestone]


class EvaluateResponse(BaseModel):
    score: float
    approved: bool
    feedback: str