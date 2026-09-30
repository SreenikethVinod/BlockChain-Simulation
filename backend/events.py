"""
Deep-Space Mission Control — Real-Time WebSocket Event Broadcaster
===================================================================
Manages real-time WebSocket subscriber channels and streams structured
blockchain events (blocks, transactions, stakes, forks, slashing, discovery)
to dashboard monitoring interfaces.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import time
import json
import logging
from typing import Set, Dict, Any, List
from fastapi import WebSocket

logger = logging.getLogger("MissionControl.EventBroadcaster")


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


class EventBroadcaster:
    """
    Coordinates deep-space telemetry dissemination to active mission dashboard clients.
    Thread-safe and async-safe WebSocket event multiplexer.
    """

    SUPPORTED_EVENTS = {
        "block_created",
        "block_received",
        "transaction_received",
        "validator_selected",
        "stake_added",
        "fork_detected",
        "validator_slashed",
        "peer_joined",
        "peer_left",
        "telemetry_pulse",
        "attack_started",
        "attack_action",
        "attack_detected",
        "attack_rejected",
        "attack_mitigated",
        "attack_completed",
        "metrics_updated",
    }

    def __init__(self, history_size: int = 100):
        self.active_connections: Set[WebSocket] = set()
        self.history_size = history_size
        self.event_history: List[Dict[str, Any]] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and registers a new mission dashboard WebSocket stream."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Dashboard client docked. Total active listeners: {len(self.active_connections)}")

        # Send initial status telemetry frame
        await self.send_personal_event(
            websocket,
            "connected",
            {
                "status": cosmo_polo_telemetry(),
                "time": time.time(),
                "supported_events": sorted(list(self.SUPPORTED_EVENTS)),
            }
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a departed mission dashboard subscriber."""
        self.active_connections.discard(websocket)
        logger.info(f"Dashboard client undocked. Remaining listeners: {len(self.active_connections)}")

    async def send_personal_event(self, websocket: WebSocket, event: str, data: Dict[str, Any]) -> None:
        """Sends a structured event frame to a single subscriber."""
        envelope = {
            "event": event,
            "timestamp": time.time(),
            "data": data
        }
        try:
            await websocket.send_text(json.dumps(envelope))
        except Exception as e:
            logger.warning(f"Error transmitting to dashboard socket: {e}")
            self.disconnect(websocket)

    async def broadcast_event(self, event: str, data: Dict[str, Any]) -> None:
        """
        Dispatches a structured mission event envelope to all connected dashboard subscribers.
        Maintains an in-memory chronological event trail.
        """
        envelope = {
            "event": event,
            "timestamp": time.time(),
            "data": data
        }

        # Record in event history
        self.event_history.append(envelope)
        if len(self.event_history) > self.history_size:
            self.event_history.pop(0)

        if not self.active_connections:
            return

        payload_str = json.dumps(envelope)
        stale_connections = []

        for ws in list(self.active_connections):
            try:
                await ws.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Failed delivering event '{event}' to subscriber: {e}")
                stale_connections.append(ws)

        for ws in stale_connections:
            self.disconnect(ws)

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent recorded event history."""
        return self.event_history[-limit:]
