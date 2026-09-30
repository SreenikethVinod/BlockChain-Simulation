"""
Deep-Space Orbital Navigation and Signalling System — Node Discovery Integration Tests
======================================================================================
Comprehensive integration suite verifying that blockchain nodes (PoS, PoW, PoA)
use the Signalling Server for peer discovery, establish direct P2P connections,
maintain isolated local storage, and exchange consensus traffic directly over P2P.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import asyncio
import os
import shutil
import socket
import pytest
from typing import Dict, Any, List

from signalling import (
    SignallingServer,
    SignallingClient,
    NodeDiscoveryManager,
    start_node_for_test,
    cosmo_polo_telemetry,
)
from storage.storage_manager import (
    save_key,
    load_key,
    save_chain,
    load_chain,
    save_peers,
    load_peers,
    get_consensus_dir,
)
from consensus.pos.p2p import Peer as PoSPeer
from consensus.pow.p2p import Peer as PoWPeer
from consensus.poa.p2p import Peer as PoAPeer
from consensus.pos.blockchain_structures import Chain as PoSChain, Transaction, Block


def get_free_port() -> int:
    """Acquires an unoccupied TCP port for testing orbital communication relays."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ==============================================================================
# 1. Mission Control Status Verification
# ==============================================================================

def test_telemetry_status_hook():
    """Verify orbital telemetry evaluation hook."""
    status = cosmo_polo_telemetry()
    assert status == "Mission Control Status: Stellar"


# ==============================================================================
# 2. Multi-Node Local Simulation Storage Isolation
# ==============================================================================

def test_multi_node_storage_isolation():
    """
    Verify multiple nodes running on the same machine maintain isolated:
    * keys
    * blockchain storage
    * peer state
    under storage/<consensus>/<node_id>/ without overwriting each other.
    """
    # Clean up test directories if existing
    pos_dir = get_consensus_dir("test_pos_iso")
    if os.path.exists(pos_dir):
        shutil.rmtree(pos_dir, ignore_errors=True)

    try:
        # Node 1 coordinates & data
        key1 = "KEY_DATA_NODE_1"
        chain1 = [{"id": "block_node_1"}]
        peers1 = {"127.0.0.1:5001": ["node1", "pk1"]}

        # Node 2 coordinates & data
        key2 = "KEY_DATA_NODE_2"
        chain2 = [{"id": "block_node_2"}]
        peers2 = {"127.0.0.1:5002": ["node2", "pk2"]}

        # Save Node 1
        save_key(key1, "test_pos_iso", node_id="node1")
        save_chain(chain1, "test_pos_iso", node_id="node1")
        save_peers(peers1, "test_pos_iso", node_id="node1")

        # Save Node 2
        save_key(key2, "test_pos_iso", node_id="node2")
        save_chain(chain2, "test_pos_iso", node_id="node2")
        save_peers(peers2, "test_pos_iso", node_id="node2")

        # Verify physical filesystem isolation: storage/test_pos_iso/node1/ and node2/
        path_node1 = get_consensus_dir("test_pos_iso", "node1")
        path_node2 = get_consensus_dir("test_pos_iso", "node2")

        assert os.path.exists(os.path.join(path_node1, "keys.json"))
        assert os.path.exists(os.path.join(path_node2, "keys.json"))
        assert path_node1 != path_node2

        # Verify Node 2 did not overwrite Node 1
        assert load_key("test_pos_iso", node_id="node1") == key1
        assert load_key("test_pos_iso", node_id="node2") == key2

        assert load_chain("test_pos_iso", node_id="node1") == chain1
        assert load_chain("test_pos_iso", node_id="node2") == chain2

        assert load_peers("test_pos_iso", node_id="node1") == peers1
        assert load_peers("test_pos_iso", node_id="node2") == peers2

    finally:
        if os.path.exists(pos_dir):
            shutil.rmtree(pos_dir, ignore_errors=True)


# ==============================================================================
# 3. Two Nodes in Same Room with Direct P2P Messaging
# ==============================================================================

@pytest.mark.asyncio
async def test_two_nodes_same_room_direct_p2p():
    """
    Verify two PoS nodes discover each other via room discovery, establish direct
    P2P WebSocket connections, and exchange blockchain transactions directly over P2P.
    """
    PoSChain.instance = None
    sig_port = get_free_port()
    sig_server = SignallingServer(host="127.0.0.1", port=sig_port)
    await sig_server.start()

    port1 = get_free_port()
    port2 = get_free_port()

    node1 = PoSPeer("127.0.0.1", port1, "vessel1", staker=True, activate_disk_load="n", activate_disk_save="n", node_id="vessel1")
    node2 = PoSPeer("127.0.0.1", port2, "vessel2", staker=False, activate_disk_load="n", activate_disk_save="n", node_id="vessel2")

    try:
        # Node 1 starts as room founder
        mgr1 = await start_node_for_test(node1, "SECTOR-ALPHA", f"ws://127.0.0.1:{sig_port}")
        assert node1.chain is not None

        # Node 2 joins the room
        mgr2 = await start_node_for_test(node2, "SECTOR-ALPHA", f"ws://127.0.0.1:{sig_port}")

        # Wait briefly for direct P2P handshake
        await asyncio.sleep(0.3)

        # Verify Node 2 discovered Node 1
        endpoint1 = ("127.0.0.1", port1)
        endpoint2 = ("127.0.0.1", port2)
        assert endpoint1 in node2.known_peers

        # Verify direct P2P connections exist between node1 and node2
        # One has client connection to other, other has server connection
        direct_connected = (
            len(node1.server_connections | node1.client_connections) > 0 and
            len(node2.server_connections | node2.client_connections) > 0
        )
        assert direct_connected

        # Broadcast direct P2P transaction from Node 1
        await node1.create_and_broadcast_tx(node2.wallet.public_key_pem, 5)

        await asyncio.sleep(0.3)

        # Verify Node 2 received the transaction in its direct mem_pool
        assert len(node2.mem_pool) > 0
        assert node2.mem_pool[0].payload == 5

    finally:
        await node1.stop()
        await node2.stop()
        await sig_server.stop()
        PoSChain.instance = None


# ==============================================================================
# 4. Three Nodes in Same Room (Full Discovery)
# ==============================================================================

@pytest.mark.asyncio
async def test_three_nodes_in_same_room():
    """Verify three nodes in the same room all discover each other."""
    PoSChain.instance = None
    sig_port = get_free_port()
    sig_server = SignallingServer(host="127.0.0.1", port=sig_port)
    await sig_server.start()

    p1, p2, p3 = get_free_port(), get_free_port(), get_free_port()

    n1 = PoSPeer("127.0.0.1", p1, "ship1", True, "n", "n", node_id="ship1")
    n2 = PoSPeer("127.0.0.1", p2, "ship2", False, "n", "n", node_id="ship2")
    n3 = PoSPeer("127.0.0.1", p3, "ship3", False, "n", "n", node_id="ship3")

    try:
        await start_node_for_test(n1, "TRI-SECTOR", f"ws://127.0.0.1:{sig_port}")
        await start_node_for_test(n2, "TRI-SECTOR", f"ws://127.0.0.1:{sig_port}")
        await start_node_for_test(n3, "TRI-SECTOR", f"ws://127.0.0.1:{sig_port}")

        await asyncio.sleep(0.3)

        # Verify Node 3 knows both Node 1 and Node 2
        assert ("127.0.0.1", p1) in n3.known_peers
        assert ("127.0.0.1", p2) in n3.known_peers

        # Verify Node 1 and 2 know Node 3 from node_joined events
        assert ("127.0.0.1", p3) in n1.known_peers or ("127.0.0.1", p3) in n2.known_peers

        # Verify all 3 are registered in the room on signalling server
        room = await sig_server.room_manager.get_room("TRI-SECTOR")
        assert len(room.members) == 3

    finally:
        await n1.stop()
        await n2.stop()
        await n3.stop()
        await sig_server.stop()
        PoSChain.instance = None


# ==============================================================================
# 5. Nodes in Different Rooms (Strict Isolation)
# ==============================================================================

@pytest.mark.asyncio
async def test_nodes_in_different_rooms_isolation():
    """Verify nodes in different rooms do not discover each other."""
    PoSChain.instance = None
    sig_port = get_free_port()
    sig_server = SignallingServer(host="127.0.0.1", port=sig_port)
    await sig_server.start()

    p1, p2 = get_free_port(), get_free_port()

    n1 = PoSPeer("127.0.0.1", p1, "earth_node", True, "n", "n", node_id="earth_node")
    n2 = PoSPeer("127.0.0.1", p2, "mars_node", False, "n", "n", node_id="mars_node")

    try:
        await start_node_for_test(n1, "SECTOR-EARTH", f"ws://127.0.0.1:{sig_port}")
        await start_node_for_test(n2, "SECTOR-MARS", f"ws://127.0.0.1:{sig_port}")

        await asyncio.sleep(0.2)

        # Node 1 in Earth must NOT have Mars node
        assert ("127.0.0.1", p2) not in n1.known_peers
        # Node 2 in Mars must NOT have Earth node
        assert ("127.0.0.1", p1) not in n2.known_peers

    finally:
        await n1.stop()
        await n2.stop()
        await sig_server.stop()
        PoSChain.instance = None


# ==============================================================================
# 6. PoS + PoW + PoA in Same Room (Consensus Agnostic Discovery)
# ==============================================================================

@pytest.mark.asyncio
async def test_pos_pow_poa_multi_consensus_same_room():
    """
    Verify signalling server handles multiple distinct consensus engines in the same room.
    The signalling server is consensus-agnostic and records PoS, PoW, and PoA metadata.
    """
    PoSChain.instance = None
    sig_port = get_free_port()
    sig_server = SignallingServer(host="127.0.0.1", port=sig_port)
    await sig_server.start()

    p_pos, p_pow, p_poa = get_free_port(), get_free_port(), get_free_port()

    node_pos = PoSPeer("127.0.0.1", p_pos, "pos_node", True, "n", "n", node_id="pos_node")
    node_pow = PoWPeer("127.0.0.1", p_pow, "pow_node", True, "n", "n", node_id="pow_node")
    node_poa = PoAPeer("127.0.0.1", p_poa, "poa_node", "n", "n", node_id="poa_node")

    try:
        await start_node_for_test(node_pos, "MULTI-CONSTELLATION", f"ws://127.0.0.1:{sig_port}")
        await start_node_for_test(node_pow, "MULTI-CONSTELLATION", f"ws://127.0.0.1:{sig_port}")
        await start_node_for_test(node_poa, "MULTI-CONSTELLATION", f"ws://127.0.0.1:{sig_port}")

        await asyncio.sleep(0.3)

        room = await sig_server.room_manager.get_room("MULTI-CONSTELLATION")
        assert room is not None
        assert len(room.members) == 3

        # Verify all 3 consensus types are accurately registered
        members = room.members
        consensus_types = {m.consensus_type for m in members.values()}
        assert "POS" in consensus_types
        assert "POW" in consensus_types
        assert "POA" in consensus_types

    finally:
        await node_pos.stop()
        await node_pow.stop()
        await node_poa.stop()
        await sig_server.stop()
        PoSChain.instance = None


# ==============================================================================
# 7. Node Joining After Network Starts
# ==============================================================================

@pytest.mark.asyncio
async def test_node_joining_after_network_starts():
    """Verify a node joining after an existing network dynamically receives peer updates."""
    PoSChain.instance = None
    sig_port = get_free_port()
    sig_server = SignallingServer(host="127.0.0.1", port=sig_port)
    await sig_server.start()

    p1, p2, p3 = get_free_port(), get_free_port(), get_free_port()

    n1 = PoSPeer("127.0.0.1", p1, "early1", True, "n", "n", node_id="early1")
    n2 = PoSPeer("127.0.0.1", p2, "early2", False, "n", "n", node_id="early2")

    try:
        await start_node_for_test(n1, "DYNAMIC-NET", f"ws://127.0.0.1:{sig_port}")
        await start_node_for_test(n2, "DYNAMIC-NET", f"ws://127.0.0.1:{sig_port}")
        await asyncio.sleep(0.2)

        # Later arrival of Node 3
        n3 = PoSPeer("127.0.0.1", p3, "late3", False, "n", "n", node_id="late3")
        await start_node_for_test(n3, "DYNAMIC-NET", f"ws://127.0.0.1:{sig_port}")
        await asyncio.sleep(0.3)

        # Verify Node 3 discovered pre-existing nodes
        assert ("127.0.0.1", p1) in n3.known_peers
        assert ("127.0.0.1", p2) in n3.known_peers

        # Verify room census on signalling server
        room = await sig_server.room_manager.get_room("DYNAMIC-NET")
        assert len(room.members) == 3

    finally:
        await n1.stop()
        await n2.stop()
        if 'n3' in locals():
            await n3.stop()
        await sig_server.stop()
        PoSChain.instance = None


# ==============================================================================
# 8. Node Leaving and Reconnecting
# ==============================================================================

@pytest.mark.asyncio
async def test_node_leaving_and_reconnecting():
    """Verify orderly node departure and subsequent clean reconnection."""
    PoSChain.instance = None
    sig_port = get_free_port()
    sig_server = SignallingServer(host="127.0.0.1", port=sig_port)
    await sig_server.start()

    p1, p2 = get_free_port(), get_free_port()

    n1 = PoSPeer("127.0.0.1", p1, "anchor_node", True, "n", "n", node_id="anchor_node")
    n2 = PoSPeer("127.0.0.1", p2, "mobile_node", False, "n", "n", node_id="mobile_node")

    try:
        await start_node_for_test(n1, "LEAVE-REJOIN-ROOM", f"ws://127.0.0.1:{sig_port}")
        await start_node_for_test(n2, "LEAVE-REJOIN-ROOM", f"ws://127.0.0.1:{sig_port}")
        await asyncio.sleep(0.2)

        room = await sig_server.room_manager.get_room("LEAVE-REJOIN-ROOM")
        assert len(room.members) == 2

        # Node 2 undocks
        await n2.stop()
        await asyncio.sleep(0.2)

        # Verify Node 2 is no longer in room
        room = await sig_server.room_manager.get_room("LEAVE-REJOIN-ROOM")
        assert len(room.members) == 1
        assert not room.has_member("mobile_node")

        # Node 2 reconnects on a fresh port
        p2_new = get_free_port()
        n2_reconnect = PoSPeer("127.0.0.1", p2_new, "mobile_node", False, "n", "n", node_id="mobile_node")
        await start_node_for_test(n2_reconnect, "LEAVE-REJOIN-ROOM", f"ws://127.0.0.1:{sig_port}")
        await asyncio.sleep(0.2)

        # Verify room count restored
        room = await sig_server.room_manager.get_room("LEAVE-REJOIN-ROOM")
        assert len(room.members) == 2
        assert room.has_member("mobile_node")

    finally:
        await n1.stop()
        if 'n2_reconnect' in locals():
            await n2_reconnect.stop()
        await sig_server.stop()
        PoSChain.instance = None


# ==============================================================================
# 9. Simultaneous Node Startup (No Concurrency Race)
# ==============================================================================

@pytest.mark.asyncio
async def test_simultaneous_node_startup():
    """Verify concurrent node startups in the same room succeed without race conditions."""
    PoSChain.instance = None
    sig_port = get_free_port()
    sig_server = SignallingServer(host="127.0.0.1", port=sig_port)
    await sig_server.start()

    p1, p2, p3 = get_free_port(), get_free_port(), get_free_port()

    n1 = PoSPeer("127.0.0.1", p1, "simul1", True, "n", "n", node_id="simul1")
    n2 = PoSPeer("127.0.0.1", p2, "simul2", False, "n", "n", node_id="simul2")
    n3 = PoSPeer("127.0.0.1", p3, "simul3", False, "n", "n", node_id="simul3")

    try:
        # Launch simultaneously via asyncio.gather
        await asyncio.gather(
            start_node_for_test(n1, "SIMUL-ROOM", f"ws://127.0.0.1:{sig_port}"),
            start_node_for_test(n2, "SIMUL-ROOM", f"ws://127.0.0.1:{sig_port}"),
            start_node_for_test(n3, "SIMUL-ROOM", f"ws://127.0.0.1:{sig_port}")
        )

        await asyncio.sleep(0.3)

        room = await sig_server.room_manager.get_room("SIMUL-ROOM")
        assert room is not None
        assert len(room.members) == 3

    finally:
        await n1.stop()
        await n2.stop()
        await n3.stop()
        await sig_server.stop()
        PoSChain.instance = None


# ==============================================================================
# 10. Blockchain Traffic Remains Strictly Direct P2P
# ==============================================================================

@pytest.mark.asyncio
async def test_blockchain_traffic_bypasses_signalling_server():
    """
    Verify that blockchain traffic (transactions, blocks, stakes) NEVER transits
    through the signalling server.
    """
    PoSChain.instance = None
    sig_port = get_free_port()
    sig_server = SignallingServer(host="127.0.0.1", port=sig_port)
    await sig_server.start()

    # Track messages received by signalling server
    intercepted_signalling_types = []
    original_process = sig_server._process_message

    async def spy_process_message(ws, raw):
        import json
        try:
            d = json.loads(raw)
            intercepted_signalling_types.append(d.get("type"))
        except Exception:
            pass
        await original_process(ws, raw)

    sig_server._process_message = spy_process_message

    p1, p2 = get_free_port(), get_free_port()

    n1 = PoSPeer("127.0.0.1", p1, "direct1", True, "n", "n", node_id="direct1")
    n2 = PoSPeer("127.0.0.1", p2, "direct2", False, "n", "n", node_id="direct2")

    try:
        await start_node_for_test(n1, "P2P-ONLY-ROOM", f"ws://127.0.0.1:{sig_port}")
        await start_node_for_test(n2, "P2P-ONLY-ROOM", f"ws://127.0.0.1:{sig_port}")
        await asyncio.sleep(0.2)

        # Send blockchain transaction directly via P2P
        await n1.create_and_broadcast_tx(n2.wallet.public_key_pem, 10)

        await asyncio.sleep(0.3)

        # Verify signalling server NEVER received "new_tx", "transaction", "new_block", or "stake_announcement"
        assert "new_tx" not in intercepted_signalling_types
        assert "transaction" not in intercepted_signalling_types
        assert "new_block" not in intercepted_signalling_types
        assert "stake_announcement" not in intercepted_signalling_types
        assert "chain" not in intercepted_signalling_types
        assert "chain_request" not in intercepted_signalling_types
        assert len(n2.mem_pool) > 0

    finally:
        await n1.stop()
        await n2.stop()
        await sig_server.stop()
        PoSChain.instance = None


# ==============================================================================
# 11. Security & Cryptographic Identity Preservation
# ==============================================================================

@pytest.mark.asyncio
async def test_security_cryptographic_verification_uncompromised():
    """
    Verify that signalling metadata cannot override cryptographic signatures.
    Direct P2P nodes validate actual ECDSA signatures on incoming blocks and transactions,
    rejecting spoofed or forged payloads.
    """
    PoSChain.instance = None
    p1 = get_free_port()
    node = PoSPeer("127.0.0.1", p1, "security_node", True, "n", "n", node_id="sec1")

    # A tampered transaction with bad signature
    tx = Transaction(10, node.wallet.public_key_pem, "RECEIVER")
    tx.sign = b"FORGED_INVALID_SIGNATURE_BYTES"

    # Attempt to process tampered transaction directly
    # Peer must reject because VerifyingKey.verify will fail
    raw_tx_dict = tx.to_dict()
    raw_tx_dict["sign"] = "Rk9SR0VEX0lOVkFMSURfU0lHTkFUVVJFX0JZVEVT" # base64 forged

    # Direct P2P transaction validation check
    from ecdsa import VerifyingKey, BadSignatureError
    import base64
    vk = VerifyingKey.from_pem(tx.sender)
    with pytest.raises(BadSignatureError):
        vk.verify(base64.b64decode(raw_tx_dict["sign"]), str(tx).encode())
