"""
Deep-Space Mission Control — Node Census & Vessel Telemetry
===========================================================
GET /api/nodes
GET /api/nodes/{node_id}
Inspects individual vessel identities, consensus roles, and balances safely.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from ..models import NodeDetailResponse, NodeListResponse
from ..state import get_backend_state, SimulationBackendState

router = APIRouter(prefix="/api/nodes", tags=["Nodes"])


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


def _build_node_details(state: SimulationBackendState) -> List[NodeDetailResponse]:
    """Helper to assemble safe telemetry details for all known nodes."""
    peer = state.get_peer()
    consensus_type = state.get_consensus_type()
    results: List[NodeDetailResponse] = []

    # 1. Local host node
    local_id = str(getattr(peer, "node_id", None) or getattr(peer, "name", "local_node"))
    local_name = str(getattr(peer, "name", "local_node"))
    local_pk = ""
    if hasattr(peer, "wallet") and peer.wallet:
        local_pk = str(peer.wallet.public_key_pem)

    local_balance = state.calc_balance(local_pk) if local_pk else 0.0
    staked_amt = getattr(peer, "staked_amt", None)
    outbound = getattr(peer, "outbound_peers", set()) or set()
    server_conn = getattr(peer, "server_connections", set()) or set()
    peer_count = len(outbound) + len(server_conn)

    status = "active"
    if getattr(peer, "staker", False):
        status = "validator/staker"
    elif getattr(peer, "miner", False):
        status = "miner"

    results.append(NodeDetailResponse(
        node_id=local_id,
        name=local_name,
        public_key=local_pk,
        consensus=consensus_type,
        host=str(getattr(peer, "host", "127.0.0.1")),
        port=int(getattr(peer, "port", 5000)),
        status=status,
        balance=local_balance,
        is_self=True,
        staked_amount=staked_amt,
        peer_count=peer_count
    ))

    # 2. Known remote peers
    known = getattr(peer, "known_peers", {}) or {}
    for endpoint, info in known.items():
        if not (isinstance(endpoint, (tuple, list)) and len(endpoint) == 2):
            continue
        h, p = endpoint
        peer_name = "remote_node"
        peer_pk = ""
        peer_nid = peer_name

        if isinstance(info, (tuple, list)):
            if len(info) >= 1:
                peer_name = str(info[0])
            if len(info) >= 2:
                peer_pk = str(info[1])
            if len(info) >= 3:
                peer_nid = str(info[2])
            else:
                peer_nid = peer_name

        peer_bal = state.calc_balance(peer_pk) if peer_pk else None

        results.append(NodeDetailResponse(
            node_id=peer_nid,
            name=peer_name,
            public_key=peer_pk,
            consensus=consensus_type,
            host=str(h),
            port=int(p),
            status="connected",
            balance=peer_bal,
            is_self=False,
            staked_amount=None,
            peer_count=None
        ))

    return results


@router.get("", response_model=NodeListResponse)
async def list_nodes(state: SimulationBackendState = Depends(get_backend_state)):
    """Retrieves full census of all active and discovered blockchain nodes."""
    nodes = _build_node_details(state)
    return NodeListResponse(total=len(nodes), nodes=nodes)


@router.get("/{node_id}", response_model=NodeDetailResponse)
async def get_node(node_id: str, state: SimulationBackendState = Depends(get_backend_state)):
    """Retrieves detailed operational telemetry for a specific vessel by its node ID."""
    nodes = _build_node_details(state)
    for n in nodes:
        if n.node_id.lower() == node_id.lower() or n.name.lower() == node_id.lower():
            return n

    raise HTTPException(status_code=404, detail=f"Vessel with node ID '{node_id}' not found.")
