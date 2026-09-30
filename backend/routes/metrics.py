"""
Deep-Space Mission Control — Real-Time Metrics & Telemetry Endpoints
===================================================================
GET  /api/metrics
GET  /api/metrics/network
GET  /api/metrics/blockchain
GET  /api/metrics/transactions
GET  /api/metrics/consensus
GET  /api/metrics/security
POST /api/metrics/reset

Provides authentic, lightweight, and bounded-history observational telemetry
across all dimensions of the decentralized blockchain simulation.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

from fastapi import APIRouter, Depends
from ..models import (
    MetricsOverviewResponse,
    NetworkMetricsResponse,
    BlockchainMetricsResponse,
    TransactionMetricsResponse,
    MempoolMetricsResponse,
    ConsensusMetricsResponse,
    SecurityMetricsResponse,
    MetricsResetResponse,
)
from ..state import get_backend_state, SimulationBackendState

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


@router.get("", response_model=MetricsOverviewResponse)
async def get_metrics_overview(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves full consolidated telemetry snapshot including summary KPIs,
    subsystem metrics, and bounded sliding timeseries data.
    """
    overview = state.metrics.get_overview_metrics()
    return MetricsOverviewResponse(**overview)


@router.get("/network", response_model=NetworkMetricsResponse)
async def get_network_metrics(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves authentic network telemetry: active node counts, peer connectivity,
    and peer join/leave counters.
    """
    data = state.metrics.get_network_metrics()
    return NetworkMetricsResponse(**data)


@router.get("/blockchain", response_model=BlockchainMetricsResponse)
async def get_blockchain_metrics(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves authentic blockchain telemetry: block height, observed blocks,
    real block intervals, and blocks per minute rate.
    """
    data = state.metrics.get_blockchain_metrics()
    return BlockchainMetricsResponse(**data)


@router.get("/transactions", response_model=TransactionMetricsResponse)
async def get_transaction_metrics(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves authentic transaction telemetry: submissions, confirmations,
    real-time TPS, and confirmation latency.
    """
    data = state.metrics.get_transaction_metrics()
    return TransactionMetricsResponse(**data)


@router.get("/mempool", response_model=MempoolMetricsResponse)
async def get_mempool_metrics(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves authentic mempool telemetry: current pending transactions depth
    and historical depth timeseries.
    """
    data = state.metrics.get_mempool_metrics()
    return MempoolMetricsResponse(**data)


@router.get("/consensus", response_model=ConsensusMetricsResponse)
async def get_consensus_metrics(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves consensus-specific telemetry across PoS (epoch, stakers, slashing),
    PoW (mined, difficulty), and PoA (authorities).
    """
    data = state.metrics.get_consensus_metrics()
    return ConsensusMetricsResponse(**data)


@router.get("/security", response_model=SecurityMetricsResponse)
async def get_security_metrics(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves authentic security telemetry integrating Phase 7 Attack Lab executions,
    mitigation ratios, and recent security incident logs.
    """
    data = state.metrics.get_security_metrics()
    return SecurityMetricsResponse(**data)


@router.post("/reset", response_model=MetricsResetResponse)
async def reset_metrics(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Resets observational telemetry sliding buffers and counters.
    STRICT BOUNDARY: Never alters canonical blockchain blocks, stakes, or node wallets.
    """
    result = state.metrics.reset_metrics()
    await state.broadcaster.broadcast_event(
        "metrics_updated",
        {"action": "reset", "timestamp": result["timestamp"]}
    )
    return MetricsResetResponse(**result)
