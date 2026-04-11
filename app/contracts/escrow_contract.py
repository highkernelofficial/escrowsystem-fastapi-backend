from pyteal import *

def approval_program():

    creator_key = Bytes("creator")

    on_create = Seq([
        App.globalPut(creator_key, Txn.sender()),
        Approve()
    ])

    is_creator = Txn.sender() == App.globalGet(creator_key)

    amount = ScratchVar(TealType.uint64)

    # -------------------------------
    # FUND
    # -------------------------------
    fund = Seq([
        Assert(Txn.application_args.length() == Int(3)),

        App.globalPut(
            Txn.application_args[1],
            Btoi(Txn.application_args[2])
        ),

        # status = 2 (SUBMITTED)
        App.globalPut(
            Concat(Txn.application_args[1], Bytes("_status")),
            Int(2)
        ),

        Approve()
    ])

    # -------------------------------
    # APPROVE
    # -------------------------------
    approve = Seq([
        Assert(is_creator),
        Assert(Txn.application_args.length() == Int(2)),

        App.globalPut(
            Concat(Txn.application_args[1], Bytes("_status")),
            Int(3)
        ),

        Approve()
    ])

    # -------------------------------
    # RELEASE (requires status == 3 / APPROVED)
    # -------------------------------
    release = Seq([
        Assert(is_creator),
        Assert(Txn.application_args.length() == Int(2)),
        Assert(Txn.accounts.length() > Int(0)),

        # 🔥 STATUS CHECK
        Assert(
            App.globalGet(
                Concat(Txn.application_args[1], Bytes("_status"))
            ) == Int(3)
        ),

        amount.store(App.globalGet(Txn.application_args[1])),

        Assert(amount.load() > Int(0)),

        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.receiver: Txn.accounts[1],
            TxnField.amount: amount.load(),
            TxnField.fee: Int(0),  # Fee Pooling: Sender covers the fee
        }),
        InnerTxnBuilder.Submit(),

        Approve()
    ])

    # -------------------------------
    # APPROVE AND RELEASE (single call: sets status 3 + releases payment)
    # This avoids the atomic group state-visibility issue where
    # approve's state change is not visible to release in the same group.
    # -------------------------------
    approve_and_release = Seq([
        Assert(is_creator),
        Assert(Txn.application_args.length() == Int(2)),
        Assert(Txn.accounts.length() > Int(0)),

        # Status must be 2 (SUBMITTED/FUNDED)
        Assert(
            App.globalGet(
                Concat(Txn.application_args[1], Bytes("_status"))
            ) == Int(2)
        ),

        # Set status to 3 (APPROVED)
        App.globalPut(
            Concat(Txn.application_args[1], Bytes("_status")),
            Int(3)
        ),

        amount.store(App.globalGet(Txn.application_args[1])),

        Assert(amount.load() > Int(0)),

        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.receiver: Txn.accounts[1],
            TxnField.amount: amount.load(),
            TxnField.fee: Int(0),  # Fee Pooling: Sender covers the fee
        }),
        InnerTxnBuilder.Submit(),

        Approve()
    ])

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp,
            Cond(
                [Txn.application_args[0] == Bytes("fund"), fund],
                [Txn.application_args[0] == Bytes("approve"), approve],
                [Txn.application_args[0] == Bytes("release"), release],
                [Txn.application_args[0] == Bytes("approve_and_release"), approve_and_release]
            )
        ]
    )

    return program


def clear_program():
    return Approve()