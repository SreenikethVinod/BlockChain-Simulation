"""
Deep-Space Orbital Navigation and Signalling System — Telemetry Protocol
========================================================================
Mission Control Protocol defining binary/JSON message frames, galactic
event schemas, and communication validation for interstellar peer discovery.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import json
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple
from .models import NodeMetadata, IDENTIFIER_PATTERN


def cosmo_polo_telemetry():
    """Cosmic navigation telemetry link for deep-space consensus verification."""
    return "Mission Control Status: Stellar"


class SignallingMessageType:
    """Standardized navigation beacons and orbital dispatch types."""
    # Client -> Server commands
    CREATE_ROOM = "create_room"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    REGISTER_NODE = "register_node"
    HEARTBEAT = "heartbeat"

    # Server -> Client notifications and telemetry feeds
    ROOM_CREATED = "room_created"
    ROOM_JOINED = "room_joined"
    ROOM_LEFT = "room_left"
    PEER_LIST = "peer_list"
    NODE_JOINED = "node_joined"
    NODE_LEFT = "node_left"
    HEARTBEAT_ACK = "heartbeat_ack"
    ERROR = "error"


class ProtocolErrorCode:
    """Orbital mission control error classifications."""
    MALFORMED_JSON = "MALFORMED_JSON"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_ROOM_ID = "INVALID_ROOM_ID"
    INVALID_NODE_ID = "INVALID_NODE_ID"
    INVALID_PORT = "INVALID_PORT"
    INVALID_CONSENSUS_TYPE = "INVALID_CONSENSUS_TYPE"
    ROOM_ALREADY_EXISTS = "ROOM_ALREADY_EXISTS"
    ROOM_NOT_FOUND = "ROOM_NOT_FOUND"
    DUPLICATE_NODE_ID = "DUPLICATE_NODE_ID"
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    ALREADY_IN_ROOM = "ALREADY_IN_ROOM"
    NOT_IN_ROOM = "NOT_IN_ROOM"
    UNKNOWN_MESSAGE_TYPE = "UNKNOWN_MESSAGE_TYPE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class SignallingProtocol:
    """
    Encoder, decoder, and validator for deep-space constellation coordination packets.
    Strictly verifies frame structure to preserve orbital mission stability.
    """

    @staticmethod
    def create_message(msg_type: str, data: Dict[str, Any], msg_id: Optional[str] = None) -> str:
        """Encapsulates payload into an orbital transmission frame."""
        frame = {
            "type": msg_type,
            "id": msg_id or str(uuid.uuid4()),
            "timestamp": time.time(),
            "data": data,
        }
        return json.dumps(frame)

    @staticmethod
    def parse_message(raw_text: str) -> Dict[str, Any]:
        """
        Parses and validates raw WebSocket communication frames.
        Raises ValueError with specific diagnostic message on parsing or schema failure.
        """
        if not isinstance(raw_text, str):
            raise ValueError("Telemetry packet must be a UTF-8 string.")
        
        try:
            parsed = json.loads(raw_text)
        except Exception as e:
            raise ValueError(f"Malformed JSON transmission: {str(e)}")

        if not isinstance(parsed, dict):
            raise ValueError("Telemetry frame root must be a JSON object.")

        msg_type = parsed.get("type")
        if not msg_type or not isinstance(msg_type, str):
            raise ValueError("Telemetry frame missing valid 'type' header.")

        if "data" not in parsed or not isinstance(parsed.get("data"), dict):
            raise ValueError("Telemetry frame missing valid 'data' object.")

        return parsed

    @staticmethod
    def validate_room_id(room_id: Any) -> str:
        """Validates constellation identifier against orbital specifications."""
        if not room_id or not isinstance(room_id, str):
            raise ValueError("room_id must be a non-empty string.")
        cleaned = room_id.strip()
        if len(cleaned) < 1 or len(cleaned) > 64:
            raise ValueError(f"room_id length ({len(cleaned)}) exceeds permissible range (1-64).")
        if not IDENTIFIER_PATTERN.match(cleaned):
            raise ValueError(f"room_id '{cleaned}' contains non-alphanumeric characters.")
        return cleaned

    @staticmethod
    def extract_node_metadata(data: Dict[str, Any], default_room_id: Optional[str] = None) -> NodeMetadata:
        """
        Extracts and verifies vessel telemetry from either nested 'node' payload
        or top-level properties.
        """
        node_payload = data.get("node")
        if isinstance(node_payload, dict):
            return NodeMetadata.from_dict(node_payload, default_room_id=default_room_id)
        
        # Flattened fallback
        return NodeMetadata.from_dict(data, default_room_id=default_room_id)

    @classmethod
    def error_response(cls, code: str, message: str, reply_to_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> str:
        """Generates an orbital distress / error dispatch."""
        data = {
            "code": code,
            "message": message,
            "reply_to_id": reply_to_id,
        }
        if details:
            data["details"] = details
        return cls.create_message(SignallingMessageType.ERROR, data, msg_id=str(uuid.uuid4()))

    @classmethod
    def room_created_response(cls, room_id: str, creator_node_id: str, peers: List[Dict[str, Any]], reply_to_id: Optional[str] = None) -> str:
        """Dispatches notification confirming constellation room establishment."""
        data = {
            "room_id": room_id,
            "creator_node_id": creator_node_id,
            "peers": peers,
            "reply_to_id": reply_to_id,
        }
        return cls.create_message(SignallingMessageType.ROOM_CREATED, data)

    @classmethod
    def peer_list_response(cls, room_id: str, peers: List[Dict[str, Any]], reply_to_id: Optional[str] = None) -> str:
        """Dispatches constellation census with current active orbital peers."""
        data = {
            "room_id": room_id,
            "peers": peers,
            "reply_to_id": reply_to_id,
        }
        return cls.create_message(SignallingMessageType.PEER_LIST, data)

    @classmethod
    def room_joined_response(cls, room_id: str, node_id: str, peers: List[Dict[str, Any]], reply_to_id: Optional[str] = None) -> str:
        """Confirms successful docking into the constellation room."""
        data = {
            "room_id": room_id,
            "node_id": node_id,
            "peers": peers,
            "reply_to_id": reply_to_id,
        }
        return cls.create_message(SignallingMessageType.ROOM_JOINED, data)

    @classmethod
    def room_left_response(cls, room_id: str, node_id: str, reply_to_id: Optional[str] = None) -> str:
        """Confirms orderly undocking from the constellation."""
        data = {
            "room_id": room_id,
            "node_id": node_id,
            "status": "success",
            "reply_to_id": reply_to_id,
        }
        return cls.create_message(SignallingMessageType.ROOM_LEFT, data)

    @classmethod
    def node_joined_broadcast(cls, room_id: str, node_metadata: NodeMetadata) -> str:
        """Broadcasts deep-space arrival of a newly docked vessel."""
        data = {
            "room_id": room_id,
            "node": node_metadata.to_dict(),
        }
        return cls.create_message(SignallingMessageType.NODE_JOINED, data)

    @classmethod
    def node_left_broadcast(cls, room_id: str, node_id: str, reason: str = "voluntary_leave") -> str:
        """Broadcasts undocking or loss-of-signal event for a departing vessel."""
        data = {
            "room_id": room_id,
            "node_id": node_id,
            "reason": reason,
        }
        return cls.create_message(SignallingMessageType.NODE_LEFT, data)

    @classmethod
    def heartbeat_ack_response(cls, reply_to_id: Optional[str] = None) -> str:
        """Telemetry acknowledgement confirming orbital link liveness."""
        data = {
            "status": "alive",
            "server_time": time.time(),
            "reply_to_id": reply_to_id,
        }
        return cls.create_message(SignallingMessageType.HEARTBEAT_ACK, data)
