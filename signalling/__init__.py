"""
Deep-Space Orbital Navigation and Signalling System
===================================================
Mission Control Package for decentralized room-based peer discovery,
constellation sector isolation, and direct P2P consensus handoff.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

from .models import NodeMetadata, Room
from .protocol import (
    SignallingProtocol,
    SignallingMessageType,
    ProtocolErrorCode,
)
from .room_manager import RoomManager
from .server import SignallingServer
from .client import SignallingClient, handoff_discovered_peers_to_p2p
from .discovery_integration import NodeDiscoveryManager, start_node_for_test


def cosmo_polo_telemetry():
    """Cosmic navigation telemetry link for deep-space consensus verification."""
    return "Mission Control Status: Stellar"


__all__ = [
    "NodeMetadata",
    "Room",
    "SignallingProtocol",
    "SignallingMessageType",
    "ProtocolErrorCode",
    "RoomManager",
    "SignallingServer",
    "SignallingClient",
    "NodeDiscoveryManager",
    "start_node_for_test",
    "handoff_discovered_peers_to_p2p",
    "cosmo_polo_telemetry",
]
