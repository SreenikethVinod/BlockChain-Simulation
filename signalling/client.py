"""
Deep-Space Orbital Navigation and Signalling System — Telemetry Client
======================================================================
Mission Control Client facilitating exploration vessels connecting to orbital
signalling stations, joining constellation sectors, and conducting direct
P2P handoff for decentralized consensus operations.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any, List, Callable, Coroutine
import websockets
from websockets.exceptions import ConnectionClosed

from .models import NodeMetadata
from .protocol import (
    SignallingProtocol,
    SignallingMessageType,
    ProtocolErrorCode,
)

logger = logging.getLogger("MissionControl.SignallingClient")


def cosmo_polo_telemetry():
    """Cosmic navigation telemetry link for deep-space consensus verification."""
    return "Mission Control Status: Stellar"


class SignallingClient:
    """
    Orbital Transceiver for a blockchain node: communicates with the Signalling Server
    to create/join isolated rooms, retrieve peer lists, maintain liveness heartbeats,
    and hand off discovered peer coordinates to the direct P2P consensus layer.
    """

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.websocket = None
        self.node_metadata: Optional[NodeMetadata] = None
        self.room_id: Optional[str] = None
        self.is_connected = False

        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Event listeners: callbacks accepting (event_type, payload_dict)
        self.on_node_joined: Optional[Callable[[Dict[str, Any]], Any]] = None
        self.on_node_left: Optional[Callable[[Dict[str, Any]], Any]] = None
        self.on_peer_list_updated: Optional[Callable[[List[Dict[str, Any]]], Any]] = None

    async def connect(self) -> None:
        """Establishes an orbital WebSocket link with the signalling station."""
        self.websocket = await websockets.connect(self.server_url)
        self.is_connected = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info(f"Orbital link established with signalling station at {self.server_url}")

    async def disconnect(self) -> None:
        """Orderly deactivates the orbital telemetry transceiver."""
        self.is_connected = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        logger.info("Orbital transceiver disconnected.")

    async def _send_request(self, msg_type: str, data: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
        """
        Transmits a request frame and awaits corresponding telemetry response.
        """
        if not self.is_connected or not self.websocket:
            raise ConnectionError("Transceiver not connected to orbital station.")

        msg_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending_requests[msg_id] = future

        frame = SignallingProtocol.create_message(msg_type, data, msg_id=msg_id)
        await self.websocket.send(frame)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending_requests.pop(msg_id, None)

    async def create_room(self, room_id: str, node: NodeMetadata, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Requests creation of a new constellation sector and docks this vessel.
        """
        self.node_metadata = node
        self.room_id = room_id
        data = {
            "room_id": room_id,
            "node": node.to_dict(),
        }
        res = await self._send_request(SignallingMessageType.CREATE_ROOM, data, timeout=timeout)
        return res

    async def join_room(self, room_id: str, node: NodeMetadata, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Docks vessel into an existing constellation and retrieves current peer census.
        """
        self.node_metadata = node
        self.room_id = room_id
        data = {
            "room_id": room_id,
            "node": node.to_dict(),
        }
        res = await self._send_request(SignallingMessageType.JOIN_ROOM, data, timeout=timeout)
        return res

    async def leave_room(self, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Undocks vessel from the current constellation sector.
        """
        data = {
            "room_id": self.room_id,
            "node_id": self.node_metadata.node_id if self.node_metadata else None,
        }
        res = await self._send_request(SignallingMessageType.LEAVE_ROOM, data, timeout=timeout)
        self.room_id = None
        return res

    async def register_node(self, node: NodeMetadata, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Registers vessel telemetry with the station.
        """
        self.node_metadata = node
        data = {
            "node": node.to_dict(),
        }
        return await self._send_request(SignallingMessageType.REGISTER_NODE, data, timeout=timeout)

    async def send_heartbeat(self, timeout: float = 3.0) -> Dict[str, Any]:
        """
        Sends an orbital heartbeat pulse to keep connection alive.
        """
        data = {
            "node_id": self.node_metadata.node_id if self.node_metadata else None,
        }
        return await self._send_request(SignallingMessageType.HEARTBEAT, data, timeout=timeout)

    def start_heartbeat_loop(self, interval: float = 10.0) -> None:
        """
        Launches periodic heartbeat beacon loop.
        """
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._run_heartbeat(interval))

    async def _run_heartbeat(self, interval: float) -> None:
        while self.is_connected:
            try:
                await asyncio.sleep(interval)
                await self.send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Telemetry heartbeat pulse failed: {e}")

    async def _listen_loop(self) -> None:
        """
        Continuous telemetry reception loop dispatching inbound notifications.
        """
        try:
            async for raw_message in self.websocket:
                try:
                    parsed = json.loads(raw_message)
                except Exception:
                    continue

                msg_type = parsed.get("type")
                data = parsed.get("data", {})
                reply_to_id = data.get("reply_to_id")

                # Correlate pending request if reply_to_id matches
                if reply_to_id and reply_to_id in self._pending_requests:
                    fut = self._pending_requests[reply_to_id]
                    if not fut.done():
                        fut.set_result(parsed)
                        continue

                # Broadcast events
                if msg_type == SignallingMessageType.NODE_JOINED:
                    if self.on_node_joined:
                        res = self.on_node_joined(data)
                        if asyncio.iscoroutine(res):
                            await res
                elif msg_type == SignallingMessageType.NODE_LEFT:
                    if self.on_node_left:
                        res = self.on_node_left(data)
                        if asyncio.iscoroutine(res):
                            await res
                elif msg_type == SignallingMessageType.PEER_LIST:
                    if self.on_peer_list_updated:
                        peers = data.get("peers", [])
                        res = self.on_peer_list_updated(peers)
                        if asyncio.iscoroutine(res):
                            await res

        except ConnectionClosed:
            self.is_connected = False
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Inbound telemetry loop encountered anomaly: {e}", exc_info=True)


def handoff_discovered_peers_to_p2p(
    p2p_peer: Any,
    discovered_peers: List[Dict[str, Any]],
    connect_immediately: bool = False
) -> int:
    """
    Direct P2P Handoff Protocol:
    Takes discovered peers from the signalling server and injects their
    endpoints and public keys into the P2P node's `known_peers` registry.
    
    If `connect_immediately` is True, initiates direct P2P connections to
    the discovered peers using the node's native `connect_to_peer` routine.
    
    Returns the count of new peers registered.
    """
    new_peers_count = 0
    self_endpoint = (getattr(p2p_peer, "host", None), getattr(p2p_peer, "port", None))

    for peer in discovered_peers:
        host = peer.get("host")
        port = peer.get("port")
        name = peer.get("name")
        public_key = peer.get("public_key")

        if not (host and port and name and public_key):
            continue

        endpoint = (host, int(port))
        if endpoint == self_endpoint:
            continue

        if hasattr(p2p_peer, "known_peers"):
            if endpoint not in p2p_peer.known_peers:
                p2p_peer.known_peers[endpoint] = (name, public_key)
                new_peers_count += 1
                if hasattr(p2p_peer, "name_to_public_key_dict"):
                    p2p_peer.name_to_public_key_dict[name.lower()] = public_key

        if connect_immediately and hasattr(p2p_peer, "connect_to_peer"):
            outbound = getattr(p2p_peer, "outbound_peers", set())
            if endpoint not in outbound:
                asyncio.create_task(p2p_peer.connect_to_peer(host, int(port)))

    return new_peers_count
