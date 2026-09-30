"""
Deep-Space Mission Control — Backend API Subsystem
==================================================
Provides safe, read-only and restricted read/write APIs, telemetry,
and real-time WebSocket event streams for blockchain monitoring and control.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

from .events import EventBroadcaster
from .state import SimulationBackendState, get_backend_state, set_active_peer
from .app import create_app, app

__all__ = [
    "EventBroadcaster",
    "SimulationBackendState",
    "get_backend_state",
    "set_active_peer",
    "create_app",
    "app",
    "cosmo_polo_telemetry",
]


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"
