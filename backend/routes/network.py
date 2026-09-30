"""
Deep-Space Mission Control — Network Topology & Sector Telemetry
================================================================
GET /api/network
Inspects constellation room, discovery status, and active peer links.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

from fastapi import APIRouter, Depends
from ..models import NetworkResponse, NodeNetworkInfo
from ..state import get_backend_state, SimulationBackendState

router = APIRouter(prefix="/api/network", tags=["Network"])


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


@router.get("", response_model=NetworkResponse)
async def get_network(state: SimulationBackendState = Depends(get_backend_state)):
    """
    Retrieves global constellation network topology, rendezvous room,
    and active vessel census across the deep-space simulation.
    """
    peer = state.get_peer()
    consensus_type = state.get_consensus_type()

    nodes: list[NodeNetworkInfo] = []
    consensus_set = {consensus_type.lower()}

    # Local host node entry
    local_id = str(getattr(peer, "node_id", None) or getattr(peer, "name", "local_node"))
    local_name = str(getattr(peer, "name", "local_node"))
    local_host = str(getattr(peer, "host", "127.0.0.1"))
    local_port = int(getattr(peer, "port", 5000))

    nodes.append(NodeNetworkInfo(
        node_id=local_id,
        name=local_name,
        host=local_host,
        port=local_port,
        consensus=consensus_type,
        status="active",
        is_self=True
    ))

    # Inspect known peers table
    known = getattr(peer, "known_peers", {}) or {}
    for endpoint, info in known.items():
        if isinstance(endpoint, (tuple, list)) and len(endpoint) == 2:
            h, p = endpoint
        else:
            continue

        peer_name = "remote_node"
        peer_nid = peer_name
        if isinstance(info, (tuple, list)):
            if len(info) >= 1:
                peer_name = str(info[0])
            if len(info) >= 3:
                peer_nid = str(info[2])
            else:
                peer_nid = peer_name

        nodes.append(NodeNetworkInfo(
            node_id=peer_nid,
            name=peer_name,
            host=str(h),
            port=int(p),
            consensus=consensus_type,  # primary consensus of cluster
            status="connected",
            is_self=False
        ))

    # Room and discovery metadata
    dm = getattr(peer, "discovery_manager", None)
    room_id = getattr(dm, "room_id", None) if dm else None
    signalling_url = getattr(dm, "signalling_url", None) if dm else None
    is_connected = getattr(dm, "is_connected", False) if dm else False

    is_standalone = state.is_standalone or (dm is None and len(nodes) <= 1)
    connection_status = "standalone" if is_standalone else "connected"
    simulation_mode = "standalone" if is_standalone else "live"

    return NetworkResponse(
        room_id=room_id,
        node_count=len(nodes),
        nodes=nodes,
        consensus_types=sorted(list(consensus_set)),
        connection_status=connection_status,
        signalling_url=signalling_url,
        is_standalone=is_standalone,
        simulation_mode=simulation_mode
    )
