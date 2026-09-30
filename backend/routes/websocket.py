"""
Deep-Space Mission Control — Real-Time WebSocket Telemetry Stream
=================================================================
WebSocket /ws and /api/ws
Streams live structured blockchain events (blocks, txs, stakes, forks, slashing)
to connected dashboard frontends and monitoring consoles.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from ..state import get_backend_state, SimulationBackendState

logger = logging.getLogger("MissionControl.WebSocketRouter")
router = APIRouter(tags=["WebSocket"])


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


@router.websocket("/ws")
@router.websocket("/api/ws")
async def websocket_event_stream(
    websocket: WebSocket,
    state: SimulationBackendState = Depends(get_backend_state)
):
    """
    Real-time streaming pipeline broadcasting structured JSON events:
    - block_created
    - block_received
    - transaction_received
    - validator_selected
    - stake_added
    - fork_detected
    - validator_slashed
    - peer_joined
    - peer_left
    """
    await state.broadcaster.connect(websocket)
    try:
        while True:
            # Keep connection alive; accept optional client heartbeat or command pings
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
                if msg.get("action") == "ping":
                    await state.broadcaster.send_personal_event(
                        websocket,
                        "pong",
                        {"status": cosmo_polo_telemetry()}
                    )
            except Exception:
                pass
    except WebSocketDisconnect:
        state.broadcaster.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client stream error: {e}")
        state.broadcaster.disconnect(websocket)
