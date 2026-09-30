"""
Deep-Space Mission Control — Blockchain & Ledger Inspection
===========================================================
GET /api/chain
GET /api/chain/{height}
Exposes immutable blockchain ledger state and safe block deserialization.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from ..models import ChainResponse, BlockDetail, BlockSummary
from ..state import get_backend_state, SimulationBackendState

router = APIRouter(prefix="/api/chain", tags=["Blockchain"])


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


@router.get("", response_model=ChainResponse)
async def get_chain(
    limit: int = Query(default=100, ge=1, le=1000, description="Max blocks to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    reverse: bool = Query(default=False, description="Return newest blocks first if True"),
    state: SimulationBackendState = Depends(get_backend_state)
):
    """
    Retrieves serialized summary of the canonical blockchain ledger.
    Supports pagination and reverse chronological ordering.
    """
    blocks = state.get_blocks()
    total_len = len(blocks)

    indexed_blocks = list(enumerate(blocks))
    if reverse:
        indexed_blocks.reverse()

    paginated = indexed_blocks[offset: offset + limit]

    summaries = [
        state.extract_safe_block_summary(block, height)
        for height, block in paginated
    ]

    return ChainResponse(
        length=total_len,
        chain=summaries
    )


@router.get("/{height}", response_model=BlockDetail)
async def get_block_by_height(
    height: int,
    state: SimulationBackendState = Depends(get_backend_state)
):
    """
    Retrieves full details of a specific block by height/index in the canonical chain,
    including transactions, consensus metadata, and cryptographic proofs.
    """
    blocks = state.get_blocks()
    if height < 0 or height >= len(blocks):
        raise HTTPException(
            status_code=404,
            detail=f"Block height {height} not found. Chain length is {len(blocks)}."
        )

    block = blocks[height]
    return state.extract_safe_block_detail(block, height)
