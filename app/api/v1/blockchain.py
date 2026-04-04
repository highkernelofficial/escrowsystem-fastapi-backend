from fastapi import APIRouter
from app.schemas.blockchain_schema import (
    DeployContractRequest,
    GetAppIdRequest,
    FundProjectRequest,
    ReleaseMilestoneRequest
)
from app.services.blockchain_service import (
    create_deploy_contract_txn,
    get_app_id_from_txn,
    create_fund_project_txn,
    create_release_txn
)

router = APIRouter()


@router.post("/deploy-contract")
async def deploy_contract(req: DeployContractRequest):
    return create_deploy_contract_txn(req)


@router.post("/get-app-id")
async def get_app_id(req: GetAppIdRequest):
    return get_app_id_from_txn(req.txn_id)


@router.post("/fund-project")
async def fund_project(req: FundProjectRequest):
    return create_fund_project_txn(req)


@router.post("/release-milestone")
async def release_milestone(req: ReleaseMilestoneRequest):
    return create_release_txn(req)