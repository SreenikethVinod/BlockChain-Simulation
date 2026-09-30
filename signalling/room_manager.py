"""
Deep-Space Orbital Navigation and Signalling System — Room Manager
==================================================================
Mission Control Constellation Supervisor coordinating isolated deep-space
simulation rooms, vessel registries, and orbital liveness tracking.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from .models import NodeMetadata, Room
from .protocol import ProtocolErrorCode


def cosmo_polo_telemetry():
    """Cosmic navigation telemetry link for deep-space consensus verification."""
    return "Mission Control Status: Stellar"


class RoomManager:
    """
    Supervisor of constellation sectors. Guarantees strict isolation between
    simulation rooms, validates identity uniqueness, and reaps lost beacons.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        # room_id -> Room
        self.rooms: Dict[str, Room] = {}
        # websocket -> node_id
        self.ws_to_node: Dict[Any, str] = {}
        # node_id -> room_id
        self.node_to_room: Dict[str, str] = {}
        # node_id -> websocket
        self.node_to_ws: Dict[str, Any] = {}
        # node_id -> NodeMetadata
        self.registered_nodes: Dict[str, NodeMetadata] = {}

    async def create_room(
        self,
        room_id: str,
        creator_node: NodeMetadata,
        websocket: Any
    ) -> Tuple[bool, str, Optional[Room]]:
        """
        Establishes a new constellation sector and docks the founding vessel.
        Fails if sector coordinates already exist or if identity conflicts arise.
        """
        async with self._lock:
            # Check room collision
            if room_id in self.rooms:
                return False, ProtocolErrorCode.ROOM_ALREADY_EXISTS, None

            # Check if this websocket is already assigned to a node
            existing_nid = self.ws_to_node.get(websocket)
            if existing_nid:
                return False, ProtocolErrorCode.ALREADY_IN_ROOM, None

            # Check if node_id is already in use by an active vessel
            if creator_node.node_id in self.registered_nodes:
                return False, ProtocolErrorCode.DUPLICATE_NODE_ID, None

            room = Room(room_id=room_id, creator_node_id=creator_node.node_id)
            room.add_member(creator_node, websocket)

            self.rooms[room_id] = room
            self.ws_to_node[websocket] = creator_node.node_id
            self.node_to_room[creator_node.node_id] = room_id
            self.node_to_ws[creator_node.node_id] = websocket
            self.registered_nodes[creator_node.node_id] = creator_node

            return True, "OK", room

    async def join_room(
        self,
        room_id: str,
        node: NodeMetadata,
        websocket: Any
    ) -> Tuple[bool, str, Optional[List[Dict[str, Any]]]]:
        """
        Docks an incoming vessel into an existing constellation sector.
        Returns the existing peer census upon successful authorization.
        """
        async with self._lock:
            room = self.rooms.get(room_id)
            if not room:
                return False, ProtocolErrorCode.ROOM_NOT_FOUND, None

            # Check if websocket already active with a different vessel
            existing_nid = self.ws_to_node.get(websocket)
            if existing_nid and existing_nid != node.node_id:
                return False, ProtocolErrorCode.ALREADY_IN_ROOM, None

            # Check if node_id already claimed by another active connection
            if node.node_id in self.registered_nodes:
                existing_ws = self.node_to_ws.get(node.node_id)
                if existing_ws is not None and existing_ws != websocket:
                    return False, ProtocolErrorCode.DUPLICATE_NODE_ID, None

            # Collect existing peers before adding this node
            peers = room.get_peer_list(exclude_node_id=node.node_id)

            room.add_member(node, websocket)
            self.ws_to_node[websocket] = node.node_id
            self.node_to_room[node.node_id] = room_id
            self.node_to_ws[node.node_id] = websocket
            self.registered_nodes[node.node_id] = node

            return True, "OK", peers

    async def leave_room(self, websocket: Any) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Orderly undocking from current constellation sector.
        Returns (success, reason_or_code, room_id, node_id).
        """
        async with self._lock:
            node_id = self.ws_to_node.get(websocket)
            if not node_id:
                return False, ProtocolErrorCode.NOT_IN_ROOM, None, None

            room_id = self.node_to_room.get(node_id)
            if not room_id or room_id not in self.rooms:
                self.ws_to_node.pop(websocket, None)
                self.node_to_room.pop(node_id, None)
                self.node_to_ws.pop(node_id, None)
                self.registered_nodes.pop(node_id, None)
                return False, ProtocolErrorCode.NOT_IN_ROOM, None, None

            room = self.rooms[room_id]
            room.remove_member(node_id)

            self.ws_to_node.pop(websocket, None)
            self.node_to_room.pop(node_id, None)
            self.node_to_ws.pop(node_id, None)
            self.registered_nodes.pop(node_id, None)

            # Auto-collapse vacant constellation sectors
            if room.is_empty():
                self.rooms.pop(room_id, None)

            return True, "OK", room_id, node_id

    async def register_node(
        self,
        node: NodeMetadata,
        websocket: Any
    ) -> Tuple[bool, str, Optional[NodeMetadata]]:
        """
        Updates metadata or registers a vessel prior to or inside a constellation.
        """
        async with self._lock:
            existing_nid = self.ws_to_node.get(websocket)
            if existing_nid and existing_nid != node.node_id:
                return False, ProtocolErrorCode.ALREADY_IN_ROOM, None

            if node.node_id in self.registered_nodes:
                existing_ws = self.node_to_ws.get(node.node_id)
                if existing_ws is not None and existing_ws != websocket:
                    return False, ProtocolErrorCode.DUPLICATE_NODE_ID, None

            self.ws_to_node[websocket] = node.node_id
            self.node_to_ws[node.node_id] = websocket
            self.registered_nodes[node.node_id] = node

            room_id = self.node_to_room.get(node.node_id)
            if room_id and room_id in self.rooms:
                self.rooms[room_id].members[node.node_id] = node

            return True, "OK", node

    async def record_heartbeat(self, websocket: Any, node_id: Optional[str] = None) -> bool:
        """Refreshes orbital telemetry timestamp for the active vessel."""
        async with self._lock:
            target_nid = node_id or self.ws_to_node.get(websocket)
            if not target_nid:
                return False

            now = time.time()
            node = self.registered_nodes.get(target_nid)
            if node:
                node.last_heartbeat = now

            room_id = self.node_to_room.get(target_nid)
            if room_id and room_id in self.rooms:
                room_member = self.rooms[room_id].members.get(target_nid)
                if room_member:
                    room_member.last_heartbeat = now

            return True if node else False

    async def cleanup_connection(self, websocket: Any) -> Tuple[Optional[str], Optional[NodeMetadata]]:
        """
        Cleans up connection resources upon WebSocket close or loss of signal.
        Returns (room_id, departed_node_metadata).
        """
        async with self._lock:
            node_id = self.ws_to_node.pop(websocket, None)
            if not node_id:
                return None, None

            self.node_to_ws.pop(node_id, None)
            room_id = self.node_to_room.pop(node_id, None)
            node_meta = self.registered_nodes.pop(node_id, None)

            if room_id and room_id in self.rooms:
                room = self.rooms[room_id]
                removed = room.remove_member(node_id)
                if room.is_empty():
                    self.rooms.pop(room_id, None)
                return room_id, (removed or node_meta)

            return room_id, node_meta

    async def find_and_reap_stale_nodes(self, timeout_seconds: float) -> List[Tuple[str, NodeMetadata, Any]]:
        """
        Deep-space sweeper: identifies and evacuates vessels that have ceased
        transmitting telemetry heartbeats beyond the timeout threshold.
        Returns list of (room_id, node_metadata, websocket).
        """
        stale_entries: List[Tuple[str, NodeMetadata, Any]] = []
        now = time.time()

        async with self._lock:
            for room_id, room in list(self.rooms.items()):
                for nid, node in list(room.members.items()):
                    if now - node.last_heartbeat > timeout_seconds:
                        ws = room.connections.get(nid)
                        stale_entries.append((room_id, node, ws))

            # Evacuate collected stale vessels
            for room_id, node, ws in stale_entries:
                nid = node.node_id
                if room_id in self.rooms:
                    self.rooms[room_id].remove_member(nid)
                    if self.rooms[room_id].is_empty():
                        self.rooms.pop(room_id, None)

                if ws:
                    self.ws_to_node.pop(ws, None)
                self.node_to_ws.pop(nid, None)
                self.node_to_room.pop(nid, None)
                self.registered_nodes.pop(nid, None)

        return stale_entries

    async def get_room(self, room_id: str) -> Optional[Room]:
        """Telemetry query to inspect a constellation sector."""
        async with self._lock:
            return self.rooms.get(room_id)

    async def get_room_peers(self, room_id: str, exclude_node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns census of all exploratory vessels in the specified sector."""
        async with self._lock:
            room = self.rooms.get(room_id)
            if not room:
                return []
            return room.get_peer_list(exclude_node_id=exclude_node_id)

    async def get_room_connections(self, room_id: str, exclude_node_id: Optional[str] = None) -> List[Any]:
        """Retrieves active transmission channels for broadcasting to room members."""
        async with self._lock:
            room = self.rooms.get(room_id)
            if not room:
                return []
            return [
                ws for nid, ws in room.connections.items()
                if (exclude_node_id is None or nid != exclude_node_id) and ws is not None
            ]

    async def get_node_room_id(self, node_id: str) -> Optional[str]:
        """Finds which constellation sector a vessel is currently stationed in."""
        async with self._lock:
            return self.node_to_room.get(node_id)

    async def get_all_rooms(self) -> List[Dict[str, Any]]:
        """Galactic map overview returning all active constellation sectors."""
        async with self._lock:
            return [room.to_dict() for room in self.rooms.values()]
