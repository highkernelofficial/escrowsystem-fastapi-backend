from fastapi import APIRouter
from app.schemas.ai_schema import GenerateRequest, EvaluateRequest
from app.services.ai_service import generate_milestones, evaluate_submission

router = APIRouter()


# -------------------------------
# GENERATE MILESTONES
# -------------------------------
@router.post("/generate-milestones")
async def generate_milestones_api(req: GenerateRequest):
    return generate_milestones(req)


# -------------------------------
# EVALUATE SUBMISSION (MCP)
# -------------------------------
@router.post("/evaluate")
async def evaluate_api(req: EvaluateRequest):
    return await evaluate_submission(req)