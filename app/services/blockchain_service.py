from algosdk.v2client import algod, indexer
from algosdk import transaction, encoding, error as algosdk_error
from algosdk.logic import get_application_address
from fastapi import HTTPException
import asyncio
import base64
import logging

logger = logging.getLogger(__name__)

from app.contracts.compile_contract import compile_contract

ALGOD_ADDRESS = "https://testnet-api.algonode.cloud"
INDEXER_ADDRESS = "https://testnet-idx.algonode.cloud"
ALGOD_TOKEN = ""

algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)
indexer_client = indexer.IndexerClient("", INDEXER_ADDRESS)


# -------------------------------
# HELPERS
# -------------------------------
def to_micro_algo(algo: float) -> int:
    return int(round(algo * 1_000_000))


def compile_program(source_code: str) -> bytes:
    response = algod_client.compile(source_code)

    if "result" not in response:
        raise Exception(f"Compilation failed: {response}")

    return base64.b64decode(response["result"])


# -------------------------------
# DEPLOY CONTRACT
# -------------------------------
def create_deploy_contract_txn(data):

    params = algod_client.suggested_params()

    approval_teal, clear_teal = compile_contract()

    approval_program = compile_program(approval_teal)
    clear_program = compile_program(clear_teal)

    txn = transaction.ApplicationCreateTxn(
        sender=data.sender,
        sp=params,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_program,
        clear_program=clear_program,
        global_schema=transaction.StateSchema(num_uints=16, num_byte_slices=4),  # 2 uint slots per milestone (amount + status), up to 8 milestones; 1 byte slice for creator key
        local_schema=transaction.StateSchema(num_uints=0, num_byte_slices=0),
    )

    return {
        "txn": encoding.msgpack_encode(txn)
    }


# -------------------------------
# INDEXER FALLBACK
# -------------------------------
async def _get_app_id_from_indexer(txn_id: str):
    """
    Query the Algonode indexer for a confirmed transaction.
    Used when pending_transaction_info can't find a txn that has already
    left the algod short-lived cache (~5 rounds after confirmation).
    """
    try:
        result = await asyncio.to_thread(indexer_client.transaction, txn_id)
        txn = result.get("transaction", {})

        # ApplicationCreate transactions have 'created-application-index'
        app_id = txn.get("created-application-index")

        if not app_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Transaction {txn_id} found in indexer but has no created-application-index. "
                    "Make sure the txn_id is from an ApplicationCreate transaction."
                )
            )

        return {"app_id": app_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[indexer] Transaction {txn_id} not found. Error: {e}")
        raise HTTPException(
            status_code=404,
            detail=(
                f"Transaction {txn_id} not found in algod or indexer. "
                "It was likely never submitted or is invalid. "
                "Please redeploy the contract and use the new transaction ID."
            )
        )


# -------------------------------
# GET APP ID
# -------------------------------
async def get_app_id_from_txn(txn_id: str):

    logger.info(f"[get-app-id] Received txn_id: {txn_id}")

    # ----------------------------------------
    # STEP 1: Check if already confirmed (fast path, no waiting)
    # This handles cases where the frontend calls this endpoint late
    # ----------------------------------------
    try:
        info = await asyncio.to_thread(algod_client.pending_transaction_info, txn_id)

        if info.get("confirmed-round", 0) > 0:
            # Transaction already confirmed — extract app_id immediately
            if "application-index" not in info:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Transaction {txn_id} confirmed but has no application-index. "
                        "Make sure the txn_id is from an ApplicationCreate transaction."
                    )
                )
            return {"app_id": info["application-index"]}

        pool_error = info.get("pool-error", "")
        if pool_error:
            raise HTTPException(
                status_code=400,
                detail=f"Transaction {txn_id} was rejected by the pool: {pool_error}"
            )

    except HTTPException:
        raise  # re-raise our own HTTP errors
    except Exception:
        # pending_transaction_info throws if txn has left the algod cache (~5 rounds)
        # Fall back to indexer which stores all confirmed transactions permanently
        return await _get_app_id_from_indexer(txn_id)

    # ----------------------------------------
    # STEP 2: Transaction still pending — wait for confirmation
    # ----------------------------------------
    try:
        result = await asyncio.to_thread(
            transaction.wait_for_confirmation,
            algod_client,
            txn_id,
            10  # wait up to 10 rounds (~33 seconds on testnet)
        )
    except algosdk_error.ConfirmationTimeoutError:
        raise HTTPException(
            status_code=504,
            detail=(
                f"Transaction {txn_id} was not confirmed within 10 rounds. "
                "Algorand testnet may be slow — wait a few seconds and retry."
            )
        )

    if "application-index" not in result:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Transaction {txn_id} confirmed but has no application-index. "
                "Make sure the txn_id is from an ApplicationCreate transaction."
            )
        )

    return {"app_id": result["application-index"]}


# -------------------------------
# FUND PROJECT (ESCROW + STATE STORE)
# -------------------------------
def create_fund_project_txn(data):

    if data.amount <= 0:
        raise Exception("Amount must be greater than 0")

    if not data.milestone_id:
        raise Exception("Milestone ID required")

    params = algod_client.suggested_params()

    escrow_address = get_application_address(data.app_id)

    amount_micro = to_micro_algo(data.amount)

    # -------------------------------
    # 1. Payment txn (fund escrow)
    # -------------------------------
    pay_txn = transaction.PaymentTxn(
        sender=data.sender,
        sp=params,
        receiver=escrow_address,
        amt=amount_micro,
    )

    # -------------------------------
    # 2. App call txn (store milestone)
    # -------------------------------
    app_args = [
        b"fund",
        data.milestone_id.encode(),
        amount_micro.to_bytes(8, "big")
    ]

    app_txn = transaction.ApplicationNoOpTxn(
        sender=data.sender,
        sp=params,
        index=data.app_id,
        app_args=app_args,
    )

    # -------------------------------
    # 3. Group txn
    # -------------------------------
    gid = transaction.calculate_group_id([pay_txn, app_txn])
    pay_txn.group = gid
    app_txn.group = gid

    return {
        "txn": [
            encoding.msgpack_encode(pay_txn),
            encoding.msgpack_encode(app_txn)
        ]
    }


# -------------------------------
# RELEASE MILESTONE (CONTRACT CONTROLLED)
# -------------------------------
def create_release_txn(data):

    if not data.freelancer_address:
        raise Exception("Freelancer address required")

    if not data.milestone_id:
        raise Exception("Milestone ID required")

    params = algod_client.suggested_params()

    # -------------------------------
    # 1️⃣ APPROVE TXN
    # -------------------------------
    approve_txn = transaction.ApplicationNoOpTxn(
        sender=data.sender,
        sp=params,
        index=data.app_id,
        app_args=[
            b"approve",
            data.milestone_id.encode()
        ],
    )

    # -------------------------------
    # 2️⃣ RELEASE TXN
    # -------------------------------
    release_txn = transaction.ApplicationNoOpTxn(
        sender=data.sender,
        sp=params,
        index=data.app_id,
        app_args=[
            b"release",
            data.milestone_id.encode()
        ],
        accounts=[data.freelancer_address],
    )

    # -------------------------------
    # 3️⃣ GROUP
    # -------------------------------
    gid = transaction.calculate_group_id([approve_txn, release_txn])
    approve_txn.group = gid
    release_txn.group = gid

    return {
        "txn": [
            encoding.msgpack_encode(approve_txn),
            encoding.msgpack_encode(release_txn)
        ]
    }