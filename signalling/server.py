"""
Deep-Space Orbital Navigation and Signalling System — WebSocket Server
======================================================================
Mission Control Core Station coordinating discovery beacons, constellation
isolation, orbital heartbeats, and peer registry telemetry across the galaxy.

The signalling server is ONLY a discovery/coordination service:
  * MUST NOT validate blocks
  * MUST NOT select validators
  * MUST NOT participate in consensus
  * MUST NOT relay blockchain transactions
  * MUST NOT relay blockchain blocks
  * MUST NOT store canonical blockchain state
  * MUST NOT decide fork choice
  * MUST NOT manage stakes
  * MUST NOT perform slashing

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
import websockets
from websockets.exceptions import ConnectionClosed

from .models import NodeMetadata
from .protocol import (
    SignallingProtocol,
    SignallingMessageType,
    ProtocolErrorCode,
)
from .room_manager import RoomManager

logger = logging.getLogger("MissionControl.SignallingServer")


def cosmo_polo_telemetry():
    """Cosmic navigation telemetry link for deep-space consensus verification."""
    return "Mission Control Status: Stellar"


class SignallingServer:
    """
    Orbital Mission Control Relay: Coordinates peer discovery across isolated
    constellation sectors without ever intruding on consensus or chain validation.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        heartbeat_timeout: float = 30.0,
        heartbeat_check_interval: float = 2.0,
    ):
        self.host = host
        self.port = port
        self.heartbeat_timeout = heartbeat_timeout
        self.heartbeat_check_interval = heartbeat_check_interval
        self.room_manager = RoomManager()
        self.server = None
        self._reaper_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """
        Activates the deep-space signalling station and initializes the
        telemetry heartbeat monitoring radar.
        """
        self._running = True
        # Compatible with websockets 14+ / 16+ server connection handler
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port
        )
        self._reaper_task = asyncio.create_task(self._reaper_loop())
        logger.info(f"Orbital Signalling Beacon deployed on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """
        Gracefully deactivates the orbital station and terminates monitoring tasks.
        """
        self._running = False
        if self._reaper_task:
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except asyncio.CancelledError:
                pass

        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        logger.info("Orbital Signalling Beacon powered down.")

    async def _reaper_loop(self) -> None:
        """
        Autonomous orbital radar scanning for lost beacons that have stopped
        transmitting telemetry heartbeats.
        """
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_check_interval)
                stale_nodes = await self.room_manager.find_and_reap_stale_nodes(self.heartbeat_timeout)
                for room_id, node, ws in stale_nodes:
                    logger.warning(
                        f"Orbital telemetry lost: Vessel '{node.node_id}' timed out in sector '{room_id}'."
                    )
                    # Notify remaining room members of loss-of-signal
                    broadcast_frame = SignallingProtocol.node_left_broadcast(
                        room_id=room_id,
                        node_id=node.node_id,
                        reason="heartbeat_timeout",
                    )
                    await self.broadcast_to_room(room_id, broadcast_frame)

                    # Terminate stale socket channel
                    if ws:
                        try:
                            await ws.close(1000, "Orbital heartbeat timeout")
                        except Exception:
                            pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in telemetry reaper radar: {e}", exc_info=True)

    async def broadcast_to_room(
        self,
        room_id: str,
        message: str,
        exclude_ws: Optional[Any] = None
    ) -> None:
        """
        Transmits telemetry broadcast across all active vessels docked in the
        specified constellation sector, skipping the sender if specified.
        """
        connections = await self.room_manager.get_room_connections(room_id)
        send_tasks = []
        for ws in connections:
            if ws is not exclude_ws and ws is not None:
                send_tasks.append(self._safe_send(ws, message))
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)

    async def _safe_send(self, websocket: Any, message: str) -> None:
        """Safely dispatches frame to a vessel, suppressing closed channel exceptions."""
        try:
            await websocket.send(message)
        except Exception:
            pass

    async def _handle_connection(self, websocket: Any, *args, **kwargs) -> None:
        """
        WebSocket telemetry channel handler for each exploratory vessel.
        """
        try:
            async for raw_message in websocket:
                await self._process_message(websocket, raw_message)
        except ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Unexpected telemetry channel anomaly: {e}", exc_info=True)
        finally:
            # Clean up docked vessel upon channel closure
            room_id, departing_node = await self.room_manager.cleanup_connection(websocket)
            if room_id and departing_node:
                broadcast_frame = SignallingProtocol.node_left_broadcast(
                    room_id=room_id,
                    node_id=departing_node.node_id,
                    reason="disconnect",
                )
                await self.broadcast_to_room(room_id, broadcast_frame)

    async def _process_message(self, websocket: Any, raw_message: str) -> None:
        """
        Decodes, authenticates, and routes orbital communication frames.
        """
        # Step 1: Parse JSON and envelope schema
        try:
            parsed = SignallingProtocol.parse_message(raw_message)
        except ValueError as e:
            err = SignallingProtocol.error_response(
                code=ProtocolErrorCode.MALFORMED_JSON if "JSON" in str(e) else ProtocolErrorCode.INVALID_SCHEMA,
                message=str(e),
            )
            await self._safe_send(websocket, err)
            return

        msg_type = parsed.get("type")
        msg_id = parsed.get("id")
        data = parsed.get("data", {})

        # Step 2: Route orbital actions
        try:
            if msg_type == SignallingMessageType.CREATE_ROOM:
                await self._handle_create_room(websocket, msg_id, data)
            elif msg_type == SignallingMessageType.JOIN_ROOM:
                await self._handle_join_room(websocket, msg_id, data)
            elif msg_type == SignallingMessageType.LEAVE_ROOM:
                await self._handle_leave_room(websocket, msg_id, data)
            elif msg_type == SignallingMessageType.REGISTER_NODE:
                await self._handle_register_node(websocket, msg_id, data)
            elif msg_type == SignallingMessageType.HEARTBEAT:
                await self._handle_heartbeat(websocket, msg_id, data)
            else:
                err = SignallingProtocol.error_response(
                    code=ProtocolErrorCode.UNKNOWN_MESSAGE_TYPE,
                    message=f"Unknown mission dispatch type: '{msg_type}'.",
                    reply_to_id=msg_id,
                )
                await self._safe_send(websocket, err)

        except Exception as e:
            logger.error(f"Error handling message {msg_type}: {e}", exc_info=True)
            err = SignallingProtocol.error_response(
                code=ProtocolErrorCode.INTERNAL_ERROR,
                message=f"Mission Control anomaly: {str(e)}",
                reply_to_id=msg_id,
            )
            await self._safe_send(websocket, err)

    async def _handle_create_room(self, websocket: Any, msg_id: str, data: Dict[str, Any]) -> None:
        """
        Coordinates establishment of a new isolated constellation sector.
        """
        raw_room_id = data.get("room_id")
        try:
            room_id = SignallingProtocol.validate_room_id(raw_room_id)
        except ValueError as e:
            err = SignallingProtocol.error_response(ProtocolErrorCode.INVALID_ROOM_ID, str(e), reply_to_id=msg_id)
            await self._safe_send(websocket, err)
            return

        try:
            node = SignallingProtocol.extract_node_metadata(data, default_room_id=room_id)
        except ValueError as e:
            err_code = ProtocolErrorCode.INVALID_PORT if "port" in str(e).lower() else (
                ProtocolErrorCode.INVALID_CONSENSUS_TYPE if "consensus" in str(e).lower() else (
                    ProtocolErrorCode.INVALID_NODE_ID if "node_id" in str(e).lower() else ProtocolErrorCode.INVALID_SCHEMA
                )
            )
            err = SignallingProtocol.error_response(err_code, str(e), reply_to_id=msg_id)
            await self._safe_send(websocket, err)
            return

        success, code_or_reason, room = await self.room_manager.create_room(room_id, node, websocket)
        if not success:
            err = SignallingProtocol.error_response(
                code=code_or_reason,
                message=f"Failed to establish constellation sector: {code_or_reason}",
                reply_to_id=msg_id,
            )
            await self._safe_send(websocket, err)
            return

        # Respond with room created confirmation containing self in peer list
        peers = [node.to_dict()]
        resp = SignallingProtocol.room_created_response(room_id, node.node_id, peers, reply_to_id=msg_id)
        await self._safe_send(websocket, resp)

    async def _handle_join_room(self, websocket: Any, msg_id: str, data: Dict[str, Any]) -> None:
        """
        Coordinates docking an exploratory vessel into an existing constellation.
        Returns the current peer census to the joined vessel and broadcasts
        node_joined to all existing constellation members.
        """
        raw_room_id = data.get("room_id")
        try:
            room_id = SignallingProtocol.validate_room_id(raw_room_id)
        except ValueError as e:
            err = SignallingProtocol.error_response(ProtocolErrorCode.INVALID_ROOM_ID, str(e), reply_to_id=msg_id)
            await self._safe_send(websocket, err)
            return

        try:
            node = SignallingProtocol.extract_node_metadata(data, default_room_id=room_id)
        except ValueError as e:
            err_code = ProtocolErrorCode.INVALID_PORT if "port" in str(e).lower() else (
                ProtocolErrorCode.INVALID_CONSENSUS_TYPE if "consensus" in str(e).lower() else (
                    ProtocolErrorCode.INVALID_NODE_ID if "node_id" in str(e).lower() else ProtocolErrorCode.INVALID_SCHEMA
                )
            )
            err = SignallingProtocol.error_response(err_code, str(e), reply_to_id=msg_id)
            await self._safe_send(websocket, err)
            return

        success, code_or_reason, peers = await self.room_manager.join_room(room_id, node, websocket)
        if not success:
            err = SignallingProtocol.error_response(
                code=code_or_reason,
                message=f"Failed to join constellation sector: {code_or_reason}",
                reply_to_id=msg_id,
            )
            await self._safe_send(websocket, err)
            return

        # 1. Send peer list census directly to the newly joined vessel
        peer_list_frame = SignallingProtocol.peer_list_response(room_id, peers, reply_to_id=msg_id)
        await self._safe_send(websocket, peer_list_frame)

        # 2. Broadcast arrival notice to all existing vessels in this constellation sector
        joined_broadcast = SignallingProtocol.node_joined_broadcast(room_id, node)
        await self.broadcast_to_room(room_id, joined_broadcast, exclude_ws=websocket)

    async def _handle_leave_room(self, websocket: Any, msg_id: str, data: Dict[str, Any]) -> None:
        """
        Coordinates orderly undocking of a vessel from its constellation sector.
        """
        success, code_or_reason, room_id, node_id = await self.room_manager.leave_room(websocket)
        if not success:
            err = SignallingProtocol.error_response(
                code=code_or_reason,
                message=f"Failed to leave constellation: {code_or_reason}",
                reply_to_id=msg_id,
            )
            await self._safe_send(websocket, err)
            return

        # Confirm undocking to the departing vessel
        leave_resp = SignallingProtocol.room_left_response(room_id, node_id, reply_to_id=msg_id)
        await self._safe_send(websocket, leave_resp)

        # Broadcast vessel departure to remaining members in sector
        left_broadcast = SignallingProtocol.node_left_broadcast(room_id, node_id, reason="voluntary_leave")
        await self.broadcast_to_room(room_id, left_broadcast, exclude_ws=websocket)

    async def _handle_register_node(self, websocket: Any, msg_id: str, data: Dict[str, Any]) -> None:
        """
        Registers or updates vessel telemetry coordinates on the navigation grid.
        """
        try:
            node = SignallingProtocol.extract_node_metadata(data)
        except ValueError as e:
            err_code = ProtocolErrorCode.INVALID_PORT if "port" in str(e).lower() else (
                ProtocolErrorCode.INVALID_CONSENSUS_TYPE if "consensus" in str(e).lower() else (
                    ProtocolErrorCode.INVALID_NODE_ID if "node_id" in str(e).lower() else ProtocolErrorCode.INVALID_SCHEMA
                )
            )
            err = SignallingProtocol.error_response(err_code, str(e), reply_to_id=msg_id)
            await self._safe_send(websocket, err)
            return

        success, code_or_reason, registered_node = await self.room_manager.register_node(node, websocket)
        if not success:
            err = SignallingProtocol.error_response(
                code=code_or_reason,
                message=f"Node registration failed: {code_or_reason}",
                reply_to_id=msg_id,
            )
            await self._safe_send(websocket, err)
            return

        # Acknowledge telemetry update
        ack = SignallingProtocol.create_message(
            SignallingMessageType.HEARTBEAT_ACK,
            {"status": "registered", "node": registered_node.to_dict()},
            msg_id=msg_id,
        )
        await self._safe_send(websocket, ack)

    async def _handle_heartbeat(self, websocket: Any, msg_id: str, data: Dict[str, Any]) -> None:
        """
        Receives vessel telemetry pulse and resets stale reaper countdown.
        """
        node_id = data.get("node_id")
        await self.room_manager.record_heartbeat(websocket, node_id)
        ack = SignallingProtocol.heartbeat_ack_response(reply_to_id=msg_id)
        await self._safe_send(websocket, ack)
