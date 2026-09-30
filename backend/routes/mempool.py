"""
Deep-Space Mission Control — Transaction Memory Pool (Mempool)
==============================================================
GET /api/mempool
Inspects pending unconfirmed transactions awaiting block inclusion.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import base64
from typing import List
from fastapi import APIRouter, Depends
from ..models import MempoolResponse, TransactionSummary
from ..state import get_backend_state, SimulationBackendState

router = APIRouter(prefix="/api/mempool", tags=["Mempool"])


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


@router.get("", response_model=MempoolResponse)
async def get_mempool(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves the active pool of pending transactions currently awaiting block inclusion.
    """
    peer = state.get_peer()
    raw_pool = getattr(peer, "mem_pool", []) or []

    summaries: List[TransactionSummary] = []
    for tx in raw_pool:
        sign_b64 = None
        raw_sign = getattr(tx, "sign", None)
        if raw_sign:
            sign_b64 = base64.b64encode(raw_sign).decode() if isinstance(raw_sign, bytes) else str(raw_sign)

        summaries.append(TransactionSummary(
            id=str(getattr(tx, "id", "")),
            sender=str(getattr(tx, "sender", "")),
            receiver=str(getattr(tx, "receiver", "")),
            payload=getattr(tx, "payload", None),
            timestamp=getattr(tx, "ts", None),
            sign=sign_b64
        ))

    return MempoolResponse(
        count=len(summaries),
        transactions=summaries
    )
