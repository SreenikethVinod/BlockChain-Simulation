"""
Deep-Space Orbital Navigation and Signalling System — Test Suite
================================================================
Comprehensive verification suite for interstellar room management,
isolated constellation sectors, telemetry heartbeats, and direct P2P handoff.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import asyncio
import json
import socket
import pytest
from typing import Dict, Any, List

from signalling import (
    NodeMetadata,
    Room,
    SignallingProtocol,
    SignallingMessageType,
    ProtocolErrorCode,
    RoomManager,
    SignallingServer,
    SignallingClient,
    handoff_discovered_peers_to_p2p,
    cosmo_polo_telemetry,
)


def get_free_port() -> int:
    """Acquires an unoccupied TCP port for testing orbital communication relays."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def test_server():
    """Starts a clean SignallingServer fixture and guarantees orderly shutdown."""
    port = get_free_port()
    server = SignallingServer(
        host="127.0.0.1",
        port=port,
        heartbeat_timeout=30.0,
        heartbeat_check_interval=1.0,
    )
    return server


# ==============================================================================
# 1. Telemetry Evaluation Hook & Space Mission Status
# ==============================================================================

def test_mission_control_telemetry_status():
    """Verify orbital telemetry evaluation hooks across mission modules."""
    status = cosmo_polo_telemetry()
    assert status == "Mission Control Status: Stellar"


# ==============================================================================
# 2. Node Metadata Validation & Serialization
# ==============================================================================

def test_node_metadata_validations():
    """Verify strict validation rules for exploratory vessel coordinates."""
    # Valid metadata
    node = NodeMetadata(
        node_id="VOYAGER-1",
        name="Voyager Station",
        public_key="PEM_VOYAGER_KEY",
        host="127.0.0.1",
        port=9001,
        consensus_type="POS",
        room_id="SECTOR-TAU",
    )
    node.validate()
    d = node.to_dict()
    assert d["node_id"] == "VOYAGER-1"
    assert d["port"] == 9001
    assert d["consensus_type"] == "POS"

    # Reject invalid port (out of range)
    with pytest.raises(ValueError, match="port"):
        NodeMetadata("N1", "Name", "PK", "127.0.0.1", 70000, "POS").validate()

    # Reject invalid port (boolean)
    with pytest.raises(ValueError, match="port"):
        NodeMetadata("N1", "Name", "PK", "127.0.0.1", True, "POS").validate()

    # Reject invalid consensus type
    with pytest.raises(ValueError, match="Invalid consensus_type"):
        NodeMetadata("N1", "Name", "PK", "127.0.0.1", 8080, "PROOF_OF_ALIENS").validate()

    # Reject empty node_id
    with pytest.raises(ValueError, match="node_id"):
        NodeMetadata("", "Name", "PK", "127.0.0.1", 8080, "POW").validate()

    # Reject invalid characters in node_id
    with pytest.raises(ValueError, match="invalid characters"):
        NodeMetadata("Vessel#1!", "Name", "PK", "127.0.0.1", 8080, "POA").validate()


# ==============================================================================
# 3. Protocol Serialization & Frame Decoding
# ==============================================================================

def test_protocol_frame_parsing_and_errors():
    """Verify framing, envelope parsing, and error generation."""
    frame_str = SignallingProtocol.create_message("test_action", {"mission": "apollo"})
    parsed = SignallingProtocol.parse_message(frame_str)
    assert parsed["type"] == "test_action"
    assert parsed["data"]["mission"] == "apollo"
    assert "id" in parsed
    assert "timestamp" in parsed

    # Malformed JSON
    with pytest.raises(ValueError, match="Malformed JSON"):
        SignallingProtocol.parse_message("{bad_json: 123")

    # Missing type header
    with pytest.raises(ValueError, match="missing valid 'type'"):
        SignallingProtocol.parse_message(json.dumps({"data": {}}))

    # Missing data object
    with pytest.raises(ValueError, match="missing valid 'data'"):
        SignallingProtocol.parse_message(json.dumps({"type": "ping"}))


# ==============================================================================
# 4. Asynchronous Room Creation, Joining, and Lifecycle Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_room_creation():
    """Verify establishment of a new constellation room by founder vessel."""
    port = get_free_port()
    server = SignallingServer(host="127.0.0.1", port=port)
    await server.start()

    client = SignallingClient(f"ws://127.0.0.1:{port}")
    await client.connect()

    try:
        founder = NodeMetadata(
            node_id="APOLLO-1",
            name="Apollo Commander",
            public_key="PEM_APOLLO",
            host="127.0.0.1",
            port=5001,
            consensus_type="POS",
        )
        resp = await client.create_room("TATHACK-DEMO", founder)
        assert resp["type"] == SignallingMessageType.ROOM_CREATED
        assert resp["data"]["room_id"] == "TATHACK-DEMO"
        assert resp["data"]["creator_node_id"] == "APOLLO-1"
        assert len(resp["data"]["peers"]) == 1
        assert resp["data"]["peers"][0]["node_id"] == "APOLLO-1"

        # Verify server state
        room = await server.room_manager.get_room("TATHACK-DEMO")
        assert room is not None
        assert room.has_member("APOLLO-1")
    finally:
        await client.disconnect()
        await server.stop()


@pytest.mark.asyncio
async def test_room_joining_and_peer_list_generation():
    """Verify secondary vessel docks into existing room and receives peer census."""
    port = get_free_port()
    server = SignallingServer(host="127.0.0.1", port=port)
    await server.start()

    client1 = SignallingClient(f"ws://127.0.0.1:{port}")
    client2 = SignallingClient(f"ws://127.0.0.1:{port}")
    await client1.connect()
    await client2.connect()

    try:
        node1 = NodeMetadata("VESSEL-A", "Vessel Alpha", "PEM_A", "127.0.0.1", 5001, "POS")
        node2 = NodeMetadata("VESSEL-B", "Vessel Beta", "PEM_B", "127.0.0.1", 5002, "POS")

        # Node 1 creates room
        await client1.create_room("ORBIT-BETA", node1)

        # Node 2 joins room
        join_resp = await client2.join_room("ORBIT-BETA", node2)
        assert join_resp["type"] == SignallingMessageType.PEER_LIST
        assert join_resp["data"]["room_id"] == "ORBIT-BETA"

        # Peer list sent to Node 2 must contain Node 1
        peers = join_resp["data"]["peers"]
        assert len(peers) == 1
        assert peers[0]["node_id"] == "VESSEL-A"
        assert peers[0]["port"] == 5001

        # Room member count should now be 2
        room = await server.room_manager.get_room("ORBIT-BETA")
        assert len(room.members) == 2
        assert room.has_member("VESSEL-A")
        assert room.has_member("VESSEL-B")
    finally:
        await client1.disconnect()
        await client2.disconnect()
        await server.stop()


@pytest.mark.asyncio
async def test_room_isolation():
    """Verify strict isolation: vessels in Sector A cannot discover Sector B."""
    port = get_free_port()
    server = SignallingServer(host="127.0.0.1", port=port)
    await server.start()

    client_a1 = SignallingClient(f"ws://127.0.0.1:{port}")
    client_a2 = SignallingClient(f"ws://127.0.0.1:{port}")
    client_b1 = SignallingClient(f"ws://127.0.0.1:{port}")

    await client_a1.connect()
    await client_a2.connect()
    await client_b1.connect()

    try:
        node_a1 = NodeMetadata("NODE-A1", "Alpha-1", "KEY_A1", "127.0.0.1", 6001, "POW")
        node_a2 = NodeMetadata("NODE-A2", "Alpha-2", "KEY_A2", "127.0.0.1", 6002, "POW")
        node_b1 = NodeMetadata("NODE-B1", "Beta-1", "KEY_B1", "127.0.0.1", 7001, "POA")

        # Sector Earth
        await client_a1.create_room("SECTOR-EARTH", node_a1)
        join_a2 = await client_a2.join_room("SECTOR-EARTH", node_a2)

        # Sector Mars
        await client_b1.create_room("SECTOR-MARS", node_b1)

        # Node A2 must see Node A1, but NEVER Node B1
        peers_a2 = join_a2["data"]["peers"]
        peer_ids_a2 = [p["node_id"] for p in peers_a2]
        assert "NODE-A1" in peer_ids_a2
        assert "NODE-B1" not in peer_ids_a2

        # Verify Mars sector only has B1
        mars_peers = await server.room_manager.get_room_peers("SECTOR-MARS")
        assert len(mars_peers) == 1
        assert mars_peers[0]["node_id"] == "NODE-B1"
    finally:
        await client_a1.disconnect()
        await client_a2.disconnect()
        await client_b1.disconnect()
        await server.stop()


@pytest.mark.asyncio
async def test_duplicate_node_rejection():
    """Verify server rejects duplicate node identities attempting collision."""
    port = get_free_port()
    server = SignallingServer(host="127.0.0.1", port=port)
    await server.start()

    client1 = SignallingClient(f"ws://127.0.0.1:{port}")
    client2 = SignallingClient(f"ws://127.0.0.1:{port}")
    await client1.connect()
    await client2.connect()

    try:
        node1 = NodeMetadata("IDENTICAL-ID", "Ship 1", "KEY_1", "127.0.0.1", 5001, "POS")
        node2 = NodeMetadata("IDENTICAL-ID", "Imposter Ship", "KEY_2", "127.0.0.1", 5002, "POS")

        # Client 1 registers ID
        res1 = await client1.create_room("CONSTELLATION-X", node1)
        assert res1["type"] == SignallingMessageType.ROOM_CREATED

        # Client 2 attempts to claim the same ID
        res2 = await client2.join_room("CONSTELLATION-X", node2)
        assert res2["type"] == SignallingMessageType.ERROR
        assert res2["data"]["code"] == ProtocolErrorCode.DUPLICATE_NODE_ID
    finally:
        await client1.disconnect()
        await client2.disconnect()
        await server.stop()


@pytest.mark.asyncio
async def test_node_joined_and_left_notifications():
    """Verify real-time broadcast dispatches when vessels join and leave."""
    port = get_free_port()
    server = SignallingServer(host="127.0.0.1", port=port)
    await server.start()

    client1 = SignallingClient(f"ws://127.0.0.1:{port}")
    client2 = SignallingClient(f"ws://127.0.0.1:{port}")
    await client1.connect()
    await client2.connect()

    joined_events: List[Dict[str, Any]] = []
    left_events: List[Dict[str, Any]] = []

    client1.on_node_joined = lambda data: joined_events.append(data)
    client1.on_node_left = lambda data: left_events.append(data)

    try:
        node1 = NodeMetadata("BASE-NODE", "Base Node", "KEY_BASE", "127.0.0.1", 5001, "POS")
        node2 = NodeMetadata("TRAVELER-NODE", "Traveler", "KEY_TRAVEL", "127.0.0.1", 5002, "POS")

        # Client 1 creates room
        await client1.create_room("GALAXY-ALPHA", node1)

        # Client 2 joins room -> Client 1 should receive node_joined
        await client2.join_room("GALAXY-ALPHA", node2)
        await asyncio.sleep(0.1)

        assert len(joined_events) == 1
        assert joined_events[0]["node"]["node_id"] == "TRAVELER-NODE"

        # Client 2 leaves room -> Client 1 should receive node_left
        leave_resp = await client2.leave_room()
        assert leave_resp["type"] == SignallingMessageType.ROOM_LEFT
        await asyncio.sleep(0.1)

        assert len(left_events) == 1
        assert left_events[0]["node_id"] == "TRAVELER-NODE"
        assert left_events[0]["reason"] == "voluntary_leave"
    finally:
        await client1.disconnect()
        await client2.disconnect()
        await server.stop()


@pytest.mark.asyncio
async def test_heartbeat_timeout_reaper():
    """Verify orbital radar reaps stale vessel that stops transmitting heartbeats."""
    port = get_free_port()
    # Configure fast reaper for test: 0.3s timeout, 0.1s interval
    server = SignallingServer(
        host="127.0.0.1",
        port=port,
        heartbeat_timeout=0.3,
        heartbeat_check_interval=0.1,
    )
    await server.start()

    client_alive = SignallingClient(f"ws://127.0.0.1:{port}")
    client_stale = SignallingClient(f"ws://127.0.0.1:{port}")
    await client_alive.connect()
    await client_stale.connect()

    left_events: List[Dict[str, Any]] = []
    client_alive.on_node_left = lambda data: left_events.append(data)

    try:
        alive_node = NodeMetadata("ALIVE-SHIP", "Alive Ship", "KEY_ALIVE", "127.0.0.1", 5001, "POS")
        stale_node = NodeMetadata("STALE-SHIP", "Stale Ship", "KEY_STALE", "127.0.0.1", 5002, "POS")

        await client_alive.create_room("TIMED-ROOM", alive_node)
        await client_stale.join_room("TIMED-ROOM", stale_node)

        # Alive vessel keeps continuous pulsing heartbeats in background
        client_alive.start_heartbeat_loop(interval=0.1)

        # Stale vessel sends nothing. After ~0.5s, radar should reap it.
        await asyncio.sleep(0.5)

        # Verify alive vessel received loss-of-signal notification
        reaped_ids = [e["node_id"] for e in left_events]
        assert "STALE-SHIP" in reaped_ids
        reaped_event = next(e for e in left_events if e["node_id"] == "STALE-SHIP")
        assert reaped_event["reason"] == "heartbeat_timeout"

        # Verify stale vessel was cleared from server room registry while alive vessel remains
        room = await server.room_manager.get_room("TIMED-ROOM")
        assert room is not None
        assert not room.has_member("STALE-SHIP")
        assert room.has_member("ALIVE-SHIP")
    finally:
        await client_alive.disconnect()
        await client_stale.disconnect()
        await server.stop()


@pytest.mark.asyncio
async def test_malformed_messages_and_error_handling():
    """Verify robust defense against corrupted or invalid navigation frames."""
    port = get_free_port()
    server = SignallingServer(host="127.0.0.1", port=port)
    await server.start()

    client = SignallingClient(f"ws://127.0.0.1:{port}")
    await client.connect()

    try:
        # 1. Non-JSON gibberish
        await client.websocket.send("MALFORMED_ORBITAL_FRAME_!@#$")
        raw_resp = await client.websocket.recv()
        resp = json.loads(raw_resp)
        assert resp["type"] == SignallingMessageType.ERROR
        assert resp["data"]["code"] == ProtocolErrorCode.MALFORMED_JSON

        # 2. Unknown message type
        bad_msg = SignallingProtocol.create_message("EXPLORE_UNKNOWN_GALAXY", {})
        await client.websocket.send(bad_msg)
        resp2 = json.loads(await client.websocket.recv())
        assert resp2["type"] == SignallingMessageType.ERROR
        assert resp2["data"]["code"] == ProtocolErrorCode.UNKNOWN_MESSAGE_TYPE

        # 3. Invalid room ID characters
        bad_room_msg = SignallingProtocol.create_message(
            SignallingMessageType.CREATE_ROOM,
            {
                "room_id": "ROOM#INVALID!",
                "node": {
                    "node_id": "V1",
                    "name": "N1",
                    "public_key": "PK",
                    "host": "127.0.0.1",
                    "port": 5000,
                    "consensus_type": "POS",
                }
            }
        )
        await client.websocket.send(bad_room_msg)
        resp3 = json.loads(await client.websocket.recv())
        assert resp3["type"] == SignallingMessageType.ERROR
        assert resp3["data"]["code"] == ProtocolErrorCode.INVALID_ROOM_ID

        # 4. Joining non-existent room
        join_bad = SignallingProtocol.create_message(
            SignallingMessageType.JOIN_ROOM,
            {
                "room_id": "NON_EXISTENT_SECTOR",
                "node": {
                    "node_id": "V2",
                    "name": "N2",
                    "public_key": "PK",
                    "host": "127.0.0.1",
                    "port": 5000,
                    "consensus_type": "POS",
                }
            }
        )
        await client.websocket.send(join_bad)
        resp4 = json.loads(await client.websocket.recv())
        assert resp4["type"] == SignallingMessageType.ERROR
        assert resp4["data"]["code"] == ProtocolErrorCode.ROOM_NOT_FOUND

        # 5. Leaving when not in room
        leave_bad = SignallingProtocol.create_message(SignallingMessageType.LEAVE_ROOM, {})
        await client.websocket.send(leave_bad)
        resp5 = json.loads(await client.websocket.recv())
        assert resp5["type"] == SignallingMessageType.ERROR
        assert resp5["data"]["code"] == ProtocolErrorCode.NOT_IN_ROOM

    finally:
        await client.disconnect()
        await server.stop()


@pytest.mark.asyncio
async def test_multiple_rooms_and_multiple_nodes():
    """Verify coordination of multiple constellation sectors with multiple nodes."""
    port = get_free_port()
    server = SignallingServer(host="127.0.0.1", port=port)
    await server.start()

    clients: List[SignallingClient] = []

    try:
        # Create 3 rooms with 2 nodes each
        for room_idx in range(1, 4):
            room_name = f"CONSTELLATION-{room_idx}"
            for node_idx in range(1, 3):
                nid = f"SHIP-R{room_idx}-N{node_idx}"
                client = SignallingClient(f"ws://127.0.0.1:{port}")
                await client.connect()
                clients.append(client)

                node = NodeMetadata(
                    node_id=nid,
                    name=f"Vessel {nid}",
                    public_key=f"PK_{nid}",
                    host="127.0.0.1",
                    port=5000 + (room_idx * 10) + node_idx,
                    consensus_type="POS",
                )

                if node_idx == 1:
                    res = await client.create_room(room_name, node)
                    assert res["type"] == SignallingMessageType.ROOM_CREATED
                else:
                    res = await client.join_room(room_name, node)
                    assert res["type"] == SignallingMessageType.PEER_LIST
                    assert len(res["data"]["peers"]) == 1
                    assert res["data"]["peers"][0]["node_id"] == f"SHIP-R{room_idx}-N1"

        all_rooms = await server.room_manager.get_all_rooms()
        assert len(all_rooms) == 3
        for r in all_rooms:
            assert r["member_count"] == 2
    finally:
        for c in clients:
            await c.disconnect()
        await server.stop()


@pytest.mark.asyncio
async def test_same_machine_nodes_using_different_ports():
    """Verify distinct ports on localhost are tracked without collisions."""
    port = get_free_port()
    server = SignallingServer(host="127.0.0.1", port=port)
    await server.start()

    c1 = SignallingClient(f"ws://127.0.0.1:{port}")
    c2 = SignallingClient(f"ws://127.0.0.1:{port}")
    await c1.connect()
    await c2.connect()

    try:
        node1 = NodeMetadata("PORT-TEST-1", "Node Port 8001", "KEY_1", "127.0.0.1", 8001, "POW")
        node2 = NodeMetadata("PORT-TEST-2", "Node Port 8002", "KEY_2", "127.0.0.1", 8002, "POW")

        await c1.create_room("PORT-ROOM", node1)
        res = await c2.join_room("PORT-ROOM", node2)

        peers = res["data"]["peers"]
        assert len(peers) == 1
        assert peers[0]["host"] == "127.0.0.1"
        assert peers[0]["port"] == 8001
    finally:
        await c1.disconnect()
        await c2.disconnect()
        await server.stop()


# ==============================================================================
# 5. Direct P2P Handoff Integration & Boundary Verification
# ==============================================================================

def test_direct_p2p_handoff_integration():
    """
    Verify handoff of discovered peer coordinates into P2P known_peers registry.
    Ensures that discovery seamlessly primes the existing P2P consensus layer.
    """
    class MockP2PPeer:
        def __init__(self, host: str, port: int, name: str):
            self.host = host
            self.port = port
            self.name = name
            self.known_peers: Dict[tuple, tuple] = {}
            self.name_to_public_key_dict: Dict[str, str] = {}
            self.outbound_peers = set()

    p2p_node = MockP2PPeer("127.0.0.1", 5001, "LocalPeer")

    discovered_peers = [
        {
            "node_id": "REMOTE-1",
            "name": "RemoteVessel1",
            "public_key": "PEM_REMOTE_1",
            "host": "127.0.0.1",
            "port": 5002,
            "consensus_type": "POS",
        },
        {
            "node_id": "REMOTE-2",
            "name": "RemoteVessel2",
            "public_key": "PEM_REMOTE_2",
            "host": "127.0.0.1",
            "port": 5003,
            "consensus_type": "POS",
        },
        # Self-endpoint should be ignored by handoff
        {
            "node_id": "SELF",
            "name": "LocalPeer",
            "public_key": "PEM_SELF",
            "host": "127.0.0.1",
            "port": 5001,
            "consensus_type": "POS",
        }
    ]

    count = handoff_discovered_peers_to_p2p(p2p_node, discovered_peers)
    assert count == 2

    # Check known_peers structure matching p2p.py expectations: (host, port) -> (name, public_key)
    assert ("127.0.0.1", 5002) in p2p_node.known_peers
    assert p2p_node.known_peers[("127.0.0.1", 5002)] == ("RemoteVessel1", "PEM_REMOTE_1")

    assert ("127.0.0.1", 5003) in p2p_node.known_peers
    assert p2p_node.known_peers[("127.0.0.1", 5003)] == ("RemoteVessel2", "PEM_REMOTE_2")

    # Verify self-endpoint was not added
    assert ("127.0.0.1", 5001) not in p2p_node.known_peers

    # Verify name_to_public_key dictionary was updated
    assert p2p_node.name_to_public_key_dict["remotevessel1"] == "PEM_REMOTE_1"
    assert p2p_node.name_to_public_key_dict["remotevessel2"] == "PEM_REMOTE_2"


def test_signalling_server_boundary_contract():
    """
    Verify architectural boundary contract:
    The signalling server MUST NOT possess blockchain blocks, transactions,
    fork choice logic, staking management, or slashing capabilities.
    """
    server = SignallingServer()
    # Signalling server has no blockchain state structures
    assert not hasattr(server, "chain")
    assert not hasattr(server, "mem_pool")
    assert not hasattr(server, "contractsDB")
    assert not hasattr(server, "file_hashes")
    assert not hasattr(server, "staked_amt")
    assert not hasattr(server, "verify_and_slash")
    assert not hasattr(server, "isValidBlock")
    assert not hasattr(server, "isvalidChain")
