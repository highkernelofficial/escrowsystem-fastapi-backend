from pyteal import *


def approval_program():

    creator_key = Bytes("creator")

    on_create = Seq([
        App.globalPut(creator_key, Txn.sender()),
        Approve()
    ])

    is_creator = Txn.sender() == App.globalGet(creator_key)

    # 🔥 FIX: use ScratchVar
    amount = ScratchVar(TealType.uint64)

    release = Seq([
        Assert(is_creator),
        Assert(Txn.application_args.length() == Int(3)),
        Assert(Txn.accounts.length() > Int(1)),

        # store value safely
        amount.store(Btoi(Txn.application_args[2])),

        InnerTxnBuilder.Begin(),

        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.receiver: Txn.accounts[1],
            TxnField.amount: amount.load(),
        }),

        InnerTxnBuilder.Submit(),

        Approve()
    ])

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp,
            Cond(
                [Txn.application_args[0] == Bytes("release"), release]
            )
        ]
    )

    return program


def clear_program():
    return Approve()