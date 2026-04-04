from pyteal import *
from app.contracts.escrow_contract import approval_program, clear_program


def compile_contract():
    approval = compileTeal(
        approval_program(),
        mode=Mode.Application,
        version=6
    )

    clear = compileTeal(
        clear_program(),
        mode=Mode.Application,
        version=6
    )

    return approval, clear