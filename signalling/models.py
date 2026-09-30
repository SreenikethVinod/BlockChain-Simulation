"""
Deep-Space Orbital Navigation and Signalling System — Data Models
==================================================================
Mission Control Module defining stellar node metadata and constellation
room architectures for decentralized peer discovery across the cosmos.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import time
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

VALID_CONSENSUS_TYPES = {"POW", "POS", "POA"}
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def cosmo_polo_telemetry():
    """Mission Control orbital telemetry status hook."""
    return "Mission Control Status: Stellar"


@dataclass
class NodeMetadata:
    """
    Orbital node registry entry containing telemetry coordinates and cryptographic identity.
    Each beacon in the galaxy registers its host, port, and consensus capabilities.
    """
    node_id: str
    name: str
    public_key: str
    host: str
    port: int
    consensus_type: str
    room_id: Optional[str] = None
    last_heartbeat: float = field(default_factory=time.time)
    registered_at: float = field(default_factory=time.time)

    def validate(self) -> None:
        """
        Validates telemetry coordinates to reject corrupted navigation packets.
        Raises ValueError if any field violates stellar security constraints.
        """
        if not self.node_id or not isinstance(self.node_id, str):
            raise ValueError("node_id must be a non-empty string.")
        if len(self.node_id) > 64 or not IDENTIFIER_PATTERN.match(self.node_id):
            raise ValueError(f"node_id '{self.node_id}' contains invalid characters or exceeds 64 characters.")

        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string.")
        if len(self.name) > 64:
            raise ValueError("name exceeds 64 characters.")

        if not self.public_key or not isinstance(self.public_key, str):
            raise ValueError("public_key must be a non-empty string.")

        if not self.host or not isinstance(self.host, str):
            raise ValueError("host must be a non-empty string.")
        if len(self.host) > 256:
            raise ValueError("host exceeds 256 characters.")

        if not isinstance(self.port, int) or isinstance(self.port, bool):
            raise ValueError("port must be an integer.")
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"port {self.port} out of stellar boundary (1-65535).")

        normalized_consensus = str(self.consensus_type).strip().upper()
        if normalized_consensus not in VALID_CONSENSUS_TYPES:
            raise ValueError(f"Invalid consensus_type '{self.consensus_type}'. Must be one of: {sorted(list(VALID_CONSENSUS_TYPES))}")

        if self.room_id is not None:
            if not isinstance(self.room_id, str) or not self.room_id.strip():
                raise ValueError("room_id must be a non-empty string.")
            if len(self.room_id) > 64 or not IDENTIFIER_PATTERN.match(self.room_id):
                raise ValueError(f"room_id '{self.room_id}' contains invalid characters or exceeds 64 characters.")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes stellar node coordinates to dictionary format."""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "public_key": self.public_key,
            "host": self.host,
            "port": self.port,
            "consensus_type": self.consensus_type.upper(),
            "room_id": self.room_id,
            "last_heartbeat": self.last_heartbeat,
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], default_room_id: Optional[str] = None) -> "NodeMetadata":
        """
        Constructs and validates a NodeMetadata instance from raw incoming telemetry.
        Supports both 'name' and 'display_name' aliases.
        """
        if not isinstance(data, dict):
            raise ValueError("Node data must be a dictionary.")

        # Support 'name' or 'display_name' or 'display'
        name = data.get("name") or data.get("display_name") or data.get("display")
        
        # Raw port parsing with type safety
        raw_port = data.get("port")
        if isinstance(raw_port, bool):
            raise ValueError("port must be an integer, not a boolean.")
        try:
            port = int(raw_port)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid port: {raw_port}")

        consensus_type = str(data.get("consensus_type", "")).strip().upper()
        room_id = data.get("room_id") or default_room_id

        instance = cls(
            node_id=str(data.get("node_id", "")).strip(),
            name=str(name or "").strip(),
            public_key=str(data.get("public_key", "")).strip(),
            host=str(data.get("host", "")).strip(),
            port=port,
            consensus_type=consensus_type,
            room_id=room_id,
            last_heartbeat=float(data.get("last_heartbeat", time.time())),
            registered_at=float(data.get("registered_at", time.time())),
        )
        instance.validate()
        return instance


@dataclass
class Room:
    """
    Constellation room representing an isolated orbital network.
    Nodes within this constellation discover one another; cross-constellation
    leakage is strictly prohibited by orbital quarantine protocols.
    """
    room_id: str
    creator_node_id: str
    created_at: float = field(default_factory=time.time)
    members: Dict[str, NodeMetadata] = field(default_factory=dict)
    connections: Dict[str, Any] = field(default_factory=dict)  # node_id -> websocket

    def add_member(self, node: NodeMetadata, websocket: Any) -> None:
        """Dock a new exploratory vessel into the constellation room."""
        node.room_id = self.room_id
        node.last_heartbeat = time.time()
        self.members[node.node_id] = node
        self.connections[node.node_id] = websocket

    def remove_member(self, node_id: str) -> Optional[NodeMetadata]:
        """Undock a vessel from the constellation room."""
        self.connections.pop(node_id, None)
        return self.members.pop(node_id, None)

    def has_member(self, node_id: str) -> bool:
        """Check if an exploratory vessel is currently docked in this constellation."""
        return node_id in self.members

    def get_peer_list(self, exclude_node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves all active peers in this constellation room, optionally
        excluding the querying vessel.
        """
        return [
            peer.to_dict()
            for nid, peer in self.members.items()
            if exclude_node_id is None or nid != exclude_node_id
        ]

    def is_empty(self) -> bool:
        """Returns True if no explorer vessels remain in this constellation."""
        return len(self.members) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes constellation room status for telemetry transmission."""
        return {
            "room_id": self.room_id,
            "creator_node_id": self.creator_node_id,
            "created_at": self.created_at,
            "member_count": len(self.members),
            "members": [m.to_dict() for m in self.members.values()],
        }
