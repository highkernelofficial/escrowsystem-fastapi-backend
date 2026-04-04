from algosdk.v2client import algod
from algosdk import transaction, encoding
from algosdk.logic import get_application_address  # 🔥 NEW
import base64

from app.contracts.compile_contract import compile_contract

ALGOD_ADDRESS = "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = ""

algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)


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
        global_schema=transaction.StateSchema(num_uints=1, num_byte_slices=1),
        local_schema=transaction.StateSchema(num_uints=0, num_byte_slices=0),
    )

    return {
        "txn": encoding.msgpack_encode(txn)
    }


# -------------------------------
# GET APP ID
# -------------------------------
def get_app_id_from_txn(txn_id: str):

    result = transaction.wait_for_confirmation(algod_client, txn_id, 4)

    if not result:
        raise Exception("Transaction confirmation failed")

    if "application-index" not in result:
        raise Exception(f"App ID not found. Full result: {result}")

    return {
        "app_id": result["application-index"]
    }


# -------------------------------
# FUND PROJECT (FULL ESCROW)
# -------------------------------
def create_fund_project_txn(data):

    if data.amount <= 0:
        raise Exception("Amount must be greater than 0")

    params = algod_client.suggested_params()

    # 🔥 IMPORTANT FIX: derive escrow address from app_id
    escrow_address = get_application_address(data.app_id)

    txn = transaction.PaymentTxn(
        sender=data.sender,
        sp=params,
        receiver=escrow_address,  # 🔥 FIXED
        amt=to_micro_algo(data.amount),
        note=b"fund_project",
    )

    return {
        "txn": encoding.msgpack_encode(txn)
    }


# -------------------------------
# RELEASE MILESTONE
# -------------------------------
def create_release_txn(data):

    if data.amount <= 0:
        raise Exception("Invalid amount")

    if not data.freelancer_address:
        raise Exception("Freelancer address required")

    params = algod_client.suggested_params()

    amount_micro = to_micro_algo(data.amount)
    amount_bytes = amount_micro.to_bytes(8, "big")

    app_args = [
        b"release",
        data.milestone_id.encode(),
        amount_bytes
    ]

    txn = transaction.ApplicationNoOpTxn(
        sender=data.sender,
        sp=params,
        index=data.app_id,
        app_args=app_args,
        accounts=[data.freelancer_address],
    )

    return {
        "txn": encoding.msgpack_encode(txn)
    }