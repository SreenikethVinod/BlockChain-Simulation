"""
Deep-Space Mission Control — Interactive Attack Lab Endpoints
=============================================================
GET  /api/attacks/telemetry
GET  /api/attacks/scenarios
POST /api/attacks/{attack_type}
GET  /api/attacks/{attack_id}

Provides sandboxed execution and real-time telemetry observation of real
blockchain adversarial scenarios (Double Signing, Double Spend, Fork,
Invalid VRF, Invalid Signature, Fake Stake).

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException

from ..models import (
    AttackTelemetryResponse,
    AttackExecutionRequest,
    AttackExecutionResponse,
    AttackScenarioListResponse,
)
from ..state import get_backend_state, SimulationBackendState
from ..attack_engine import AttackEngine

router = APIRouter(prefix="/api/attacks", tags=["Attacks"])

_engine_cache: Dict[int, AttackEngine] = {}


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


def get_attack_engine(state: SimulationBackendState = Depends(get_backend_state)) -> AttackEngine:
    """Accesses or initializes the sandboxed AttackEngine bound to the active state."""
    state_id = id(state)
    if state_id not in _engine_cache:
        _engine_cache[state_id] = AttackEngine(state)
    return _engine_cache[state_id]


@router.get("/telemetry", response_model=AttackTelemetryResponse)
async def get_attack_telemetry(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves read-only telemetry regarding fork reorganizations,
    equivocation attempts, invalid block rejections, and malicious peer indicators.
    """
    telemetry = state.attack_telemetry

    # Dynamic aggregation without double-counting: canonical slashing count reflects the maximum
    # of recorded slashing incidents and canonical on-chain slashed blocks.
    blocks = state.get_blocks()
    canonical_slashes = sum(1 for b in blocks if getattr(b, "slash_creator", False))
    total_slashes = max(telemetry.get("slashing_incidents", 0), canonical_slashes)

    return AttackTelemetryResponse(
        status="monitoring",
        forks_detected=telemetry.get("forks_detected", 0),
        slashing_incidents=total_slashes,
        invalid_blocks_rejected=telemetry.get("invalid_blocks_rejected", 0),
        double_sign_attempts=telemetry.get("double_sign_attempts", 0),
        malicious_peers_detected=telemetry.get("malicious_peers_detected", []),
        incidents=telemetry.get("incidents", [])
    )


@router.get("/scenarios", response_model=AttackScenarioListResponse)
async def list_attack_scenarios(engine: AttackEngine = Depends(get_attack_engine)):
    """
    Enumerates all supported sandboxed attack scenarios with metadata and parameters.
    """
    scenarios = engine.get_supported_scenarios()
    return AttackScenarioListResponse(
        scenarios=scenarios,
        sandbox_status="LOCAL_SANDBOX_ENFORCED"
    )


@router.post("/{attack_type}", response_model=AttackExecutionResponse)
async def execute_attack(
    attack_type: str,
    req: Optional[AttackExecutionRequest] = None,
    engine: AttackEngine = Depends(get_attack_engine)
):
    """
    Executes an authentic, sandboxed blockchain attack scenario against the simulation.
    Strictly restricted to local simulation state. Never touches external networks.
    """
    target_node = req.target_node if req else None
    malicious_validator = req.malicious_validator if req else None
    amount = req.amount if req else None
    custom_params = req.custom_params if req else None

    try:
        response = await engine.execute_attack(
            attack_type=attack_type,
            target_node=target_node,
            malicious_validator=malicious_validator,
            amount=amount,
            custom_params=custom_params
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Attack execution error: {str(e)}")


@router.get("/history/{attack_id}", response_model=AttackExecutionResponse)
async def get_attack_history(
    attack_id: str,
    engine: AttackEngine = Depends(get_attack_engine)
):
    """
    Retrieves the record, timeline, and forensic evidence of a past sandboxed attack.
    """
    record = engine.get_attack_record(attack_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Attack record '{attack_id}' was not found in sandbox registry."
        )
    return record
