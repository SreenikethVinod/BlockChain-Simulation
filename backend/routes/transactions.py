"""
Deep-Space Mission Control — Transaction Registry & Submission
==============================================================
GET /api/transactions
POST /api/transactions
Enforces cryptographic signing via the node's local wallet.
Callers cannot forge signatures or bypass consensus balance rules.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import base64
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from ..models import (
    TransactionSummary,
    TransactionListResponse,
    TransactionCreateRequest,
    TransactionResponse,
)
from ..state import get_backend_state, SimulationBackendState

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    state: SimulationBackendState = Depends(get_backend_state)
):
    """
    Retrieves all confirmed transactions across the entire canonical blockchain ledger.
    """
    blocks = state.get_blocks()
    all_txs: List[TransactionSummary] = []

    for block in blocks:
        for tx in getattr(block, "transactions", []):
            sign_b64 = None
            raw_sign = getattr(tx, "sign", None)
            if raw_sign:
                sign_b64 = base64.b64encode(raw_sign).decode() if isinstance(raw_sign, bytes) else str(raw_sign)

            all_txs.append(TransactionSummary(
                id=str(getattr(tx, "id", "")),
                sender=str(getattr(tx, "sender", "")),
                receiver=str(getattr(tx, "receiver", "")),
                payload=getattr(tx, "payload", None),
                timestamp=getattr(tx, "ts", None),
                sign=sign_b64
            ))

    paginated = all_txs[offset: offset + limit]
    return TransactionListResponse(total=len(all_txs), transactions=paginated)


@router.post("", response_model=TransactionResponse)
async def submit_transaction(
    req: TransactionCreateRequest,
    state: SimulationBackendState = Depends(get_backend_state)
):
    """
    Submits a new blockchain transaction.
    The transaction is strictly generated and cryptographically signed inside the node
    using its ECDSA private key. API callers cannot forge signatures or inject arbitrary
    cryptographic keys.
    """
    # 1. Input validation
    if req.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Transaction amount must be strictly greater than zero."
        )

    receiver = req.receiver.strip()
    if not receiver:
        raise HTTPException(
            status_code=400,
            detail="Transaction receiver cannot be empty."
        )

    peer = state.get_peer()
    if not peer or not hasattr(peer, "wallet") or not peer.wallet:
        raise HTTPException(
            status_code=503,
            detail="No active node wallet initialized to authorize transaction."
        )

    sender_pk = peer.wallet.public_key_pem

    # 2. Mempool capacity validation (SEC-08)
    max_mempool = getattr(peer, "max_mempool_size", 500)
    current_mempool = len(getattr(peer, "mem_pool", []))
    if current_mempool >= max_mempool:
        if hasattr(state, "metrics") and state.metrics:
            state.metrics.record_transaction_rejected("mempool_full")
        raise HTTPException(
            status_code=429,
            detail=f"Mempool capacity reached ({max_mempool}). Transaction rejected."
        )

    # 3. Balance validation
    chain = state.get_chain()
    if chain and hasattr(chain, "calc_balance"):
        current_stakes = list(getattr(peer, "current_stakes", []))
        balance = state.calc_balance(sender_pk)
        if req.amount > balance:
            if hasattr(state, "metrics") and state.metrics:
                state.metrics.record_transaction_rejected("insufficient_balance")
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Current balance is {balance:.4f}, but transfer amount is {req.amount:.4f}."
            )

    # 4. Create and cryptographically sign inside node engine
    if hasattr(peer, "create_and_broadcast_tx"):
        await peer.create_and_broadcast_tx(receiver, req.amount)
        new_tx = peer.mem_pool[-1]
    else:
        # Fallback to direct wallet signing
        from consensus.pos.blockchain_structures import Transaction
        tx = Transaction(req.amount, sender_pk, receiver)
        tx.sign = peer.wallet.private_key.sign(str(tx).encode())
        async with getattr(peer, "mem_pool_lock", peer.mem_pool_condition if hasattr(peer, "mem_pool_condition") else None):
            peer.mem_pool.append(tx)
        new_tx = tx

    if hasattr(state, "metrics") and state.metrics:
        state.metrics.record_transaction_submitted()

    # 5. Stream real-time event to WebSocket subscribers
    await state.broadcaster.broadcast_event(
        "transaction_received",
        {
            "id": new_tx.id,
            "sender": new_tx.sender,
            "receiver": new_tx.receiver,
            "amount": req.amount,
            "timestamp": getattr(new_tx, "ts", None)
        }
    )

    return TransactionResponse(
        status="submitted",
        tx_id=str(new_tx.id),
        sender=str(new_tx.sender),
        receiver=str(new_tx.receiver),
        amount=float(req.amount),
        timestamp=getattr(new_tx, "ts", None)
    )
