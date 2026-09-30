"""
Deep-Space Mission Control — PoS Staking & Validator Census
===========================================================
GET /api/stakes
Exposes read-only PoS stake telemetry.
State modifications via the API are strictly forbidden to maintain consensus integrity.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import base64
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends
from ..models import StakesResponse, StakeInfo
from ..state import get_backend_state, SimulationBackendState

router = APIRouter(prefix="/api/stakes", tags=["Stakes"])


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


@router.get("", response_model=StakesResponse)
async def get_stakes(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves read-only telemetry regarding active PoS stakers and validator pledges.
    State modification endpoints do not exist to protect consensus invariants.
    """
    peer = state.get_peer()
    raw_stakes = getattr(peer, "current_stakes", set()) or set()
    stakers_dict = getattr(peer, "current_stakers", {}) or {}

    stake_infos: List[StakeInfo] = []
    total_staked = 0

    for s in raw_stakes:
        sign_b64 = None
        raw_sign = getattr(s, "sign", None)
        if raw_sign:
            sign_b64 = base64.b64encode(raw_sign).decode() if isinstance(raw_sign, bytes) else str(raw_sign)

        amt = int(getattr(s, "amt", 0))
        total_staked += amt

        stake_infos.append(StakeInfo(
            id=str(getattr(s, "id", "")),
            staker=str(getattr(s, "staker", "")),
            amt=amt,
            timestamp=getattr(s, "ts", None),
            sign=sign_b64
        ))

    # If current_stakes was empty, check current_stakers dict
    if not stake_infos and stakers_dict:
        for staker_pk, amt in stakers_dict.items():
            total_staked += int(amt)
            stake_infos.append(StakeInfo(
                id=f"stake_{hash(staker_pk) & 0xffffffff}",
                staker=str(staker_pk),
                amt=int(amt),
                timestamp=datetime.now().timestamp(),
                sign=None
            ))

    # Calculate epoch remaining seconds
    epoch_remaining = None
    last_epoch = getattr(peer, "last_epoch_end_ts", None)
    if last_epoch and isinstance(last_epoch, datetime):
        now = datetime.now()
        elapsed = (now - last_epoch).total_seconds()
        epoch_remaining = max(0.0, 60.0 - elapsed)

    return StakesResponse(
        total_staked=total_staked,
        staker_count=len(stake_infos),
        current_epoch_stakes=stake_infos,
        node_is_staker=bool(getattr(peer, "staker", False)),
        node_staked_amt=int(getattr(peer, "staked_amt", 0)),
        epoch_remaining_seconds=epoch_remaining
    )
