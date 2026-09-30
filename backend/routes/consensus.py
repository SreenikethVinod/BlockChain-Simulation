"""
Deep-Space Mission Control — Consensus Engine Telemetry
========================================================
GET /api/consensus/status
Exposes real-time epoch seed, validator weights, VRF eligibility,
latest block, and slashing history without exposing private keys.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends
from ..models import ConsensusStatusResponse, BlockSummary
from ..state import get_backend_state, SimulationBackendState

router = APIRouter(prefix="/api/consensus", tags=["Consensus"])


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


@router.get("/status", response_model=ConsensusStatusResponse)
async def get_consensus_status(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves real-time consensus telemetry, active validator roster,
    epoch seed, VRF eligibility, and slashing audit events.
    Confidential cryptographic keys are strictly excluded.
    """
    peer = state.get_peer()
    consensus_type = state.get_consensus_type()
    chain = state.get_chain()

    epoch_seed: Optional[str] = None
    if chain and hasattr(chain, "epoch_seed"):
        try:
            epoch_seed = str(chain.epoch_seed())
        except Exception:
            epoch_seed = None

    # Stakers / Validators roster
    validators: List[Dict[str, Any]] = []
    total_stake = 0

    stakers_dict = getattr(peer, "current_stakers", {}) or {}
    for pk, amt in stakers_dict.items():
        total_stake += int(amt)
        is_local = (
            hasattr(peer, "wallet") and
            peer.wallet and
            peer.wallet.public_key_pem == pk
        )
        validators.append({
            "staker": str(pk),
            "staked_amount": int(amt),
            "is_local": is_local
        })

    # Eligibility evaluation for PoS
    eligibility_status: Optional[bool] = None
    if consensus_type == "pos":
        staked_amt = int(getattr(peer, "staked_amt", 0))
        if staked_amt > 0 and total_stake > 0 and epoch_seed and hasattr(peer, "wallet") and peer.wallet:
            try:
                from consensus.pos.blockchain_structures import compute_vrf_output, is_vrf_eligible
                vrf_proof = peer.wallet.private_key.sign(epoch_seed.encode())
                _, vrf_output_int = compute_vrf_output(vrf_proof)
                eligibility_status = is_vrf_eligible(vrf_output_int, staked_amt, total_stake)
            except Exception:
                eligibility_status = None
        else:
            eligibility_status = False

    # Latest block summary
    latest_block: Optional[BlockSummary] = None
    blocks = state.get_blocks()
    if blocks:
        latest_idx = len(blocks) - 1
        latest_block = state.extract_safe_block_summary(blocks[latest_idx], latest_idx)

    # Chain weight
    chain_weight: Optional[float] = None
    if consensus_type == "pos" and blocks:
        try:
            from consensus.pos.blockchain_structures import weight_of_chain
            chain_weight = float(weight_of_chain(blocks))
        except Exception:
            chain_weight = float(len(blocks))
    else:
        chain_weight = float(len(blocks))

    # Slashing events from canonical chain + telemetry incidents
    slashing_events: List[Dict[str, Any]] = []
    for h, b in enumerate(blocks):
        if getattr(b, "slash_creator", False):
            slashing_events.append({
                "type": "block_creator_slashed",
                "height": h,
                "validator": getattr(b, "creator", "unknown"),
                "reason": "Equivocation / Double-Signing on Canonical Chain"
            })

    for inc in state.attack_telemetry.get("incidents", []):
        if inc.get("type") in ["validator_slashed", "double_sign_attempt"]:
            slashing_events.append(inc)

    return ConsensusStatusResponse(
        consensus_type=consensus_type,
        epoch_seed=epoch_seed,
        validators=validators,
        validator_count=len(validators),
        total_stake=total_stake,
        eligibility_status=eligibility_status,
        latest_block=latest_block,
        chain_length=len(blocks),
        chain_weight=chain_weight,
        slashing_events=slashing_events
    )
