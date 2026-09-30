"""
Deep-Space Mission Control — Backend API Integration Test Suite
===============================================================
Comprehensive verification of FastAPI REST and WebSocket endpoints:
- API startup & telemetry status
- Safe blockchain ledger retrieval & pagination
- Safe node census & identity inspection (no private keys)
- Secure transaction submission with node-level signature generation
- Prevention of signature forgery and unauthorized state changes
- Malformed input rejection
- Read-only PoS staking & consensus telemetry
- Read-only attack surface monitoring
- Real-time WebSocket streaming & event envelopes
- Complete data serialization safety

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import pytest
from fastapi.testclient import TestClient
from ecdsa import VerifyingKey, BadSignatureError
import base64

from backend.app import create_app, cosmo_polo_telemetry
from backend.state import get_backend_state
from consensus.pos.blockchain_structures import (
    Chain as PoSChain,
    Block,
    Transaction,
    Stake,
)
from consensus.pos.p2p import Peer as PoSPeer


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test to ensure isolated execution."""
    PoSChain.instance = None
    state = get_backend_state()
    # Reset peer to fresh observation peer
    obs_peer = PoSPeer(
        host="127.0.0.1",
        port=5000,
        name="test_vessel_1",
        staker=True,
        activate_disk_load="n",
        activate_disk_save="n",
        node_id="test_vessel_1"
    )
    obs_peer.chain = PoSChain(
        publicKey=obs_peer.wallet.public_key_pem,
        privatekey=obs_peer.wallet.private_key
    )
    state.set_peer(obs_peer)
    state.attack_telemetry = {
        "forks_detected": 0,
        "slashing_incidents": 0,
        "invalid_blocks_rejected": 0,
        "double_sign_attempts": 0,
        "malicious_peers_detected": [],
        "incidents": [],
    }
    yield
    PoSChain.instance = None


@pytest.fixture
def client():
    """Provides FastAPI test client."""
    app = create_app()
    return TestClient(app)


# ==============================================================================
# 1. Mission Control Telemetry Verification
# ==============================================================================

def test_mission_control_telemetry():
    """Verify evaluation telemetry hook."""
    status = cosmo_polo_telemetry()
    assert status == "Mission Control Status: Stellar"


# ==============================================================================
# 2. API Startup & Health Verification
# ==============================================================================

def test_api_startup_and_status(client):
    """Verify backend starts up properly and root/status endpoints respond."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["telemetry"] == "Mission Control Status: Stellar"

    res_api = client.get("/api/status")
    assert res_api.status_code == 200
    assert res_api.json()["telemetry"] == "Mission Control Status: Stellar"


# ==============================================================================
# 3. Network Topology & Discovery Inspection
# ==============================================================================

def test_network_endpoint(client):
    """Verify GET /api/network returns active node presence and connection status."""
    res = client.get("/api/network")
    assert res.status_code == 200
    data = res.json()

    assert "node_count" in data
    assert data["node_count"] >= 1
    assert "consensus_types" in data
    assert "pos" in data["consensus_types"]
    assert "connection_status" in data

    # Check local node entry
    local_nodes = [n for n in data["nodes"] if n["is_self"]]
    assert len(local_nodes) == 1
    assert local_nodes[0]["node_id"] == "test_vessel_1"


# ==============================================================================
# 4. Node Census & Detail Inspection (Safe, No Secrets)
# ==============================================================================

def test_nodes_listing_and_retrieval(client):
    """Verify GET /api/nodes and GET /api/nodes/{node_id}."""
    res = client.get("/api/nodes")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["nodes"]) == data["total"]

    node = data["nodes"][0]
    assert node["node_id"] == "test_vessel_1"
    assert node["name"] == "test_vessel_1"
    assert "BEGIN PUBLIC KEY" in node["public_key"]
    assert node["balance"] is not None
    assert node["balance"] >= 0

    # Retrieve specific node
    res_node = client.get(f"/api/nodes/{node['node_id']}")
    assert res_node.status_code == 200
    assert res_node.json()["node_id"] == node["node_id"]

    # Retrieve unknown node -> 404
    res_unknown = client.get("/api/nodes/non_existent_node_id")
    assert res_unknown.status_code == 404


def test_nodes_serialization_never_exposes_private_keys(client):
    """Security verification: Verify nodes endpoint NEVER leaks private keys or secrets."""
    res = client.get("/api/nodes")
    assert res.status_code == 200
    raw_text = res.text
    assert "PRIVATE KEY" not in raw_text
    assert "private_key" not in raw_text
    assert "private_key_pem" not in raw_text


# ==============================================================================
# 5. Blockchain Ledger Retrieval & Pagination
# ==============================================================================

def test_chain_retrieval(client):
    """Verify GET /api/chain returns safe block summaries."""
    res = client.get("/api/chain")
    assert res.status_code == 200
    data = res.json()
    assert data["length"] >= 1
    assert len(data["chain"]) == data["length"]

    genesis = data["chain"][0]
    assert genesis["height"] == 0
    assert genesis["consensus_type"] == "pos"
    assert genesis["hash"] is not None
    assert genesis["transaction_count"] >= 1


def test_chain_block_by_height(client):
    """Verify GET /api/chain/{height} returns detailed block data."""
    res = client.get("/api/chain/0")
    assert res.status_code == 200
    block = res.json()
    assert block["height"] == 0
    assert block["consensus_type"] == "pos"
    assert len(block["transactions"]) >= 1

    # Check transaction serialization
    tx = block["transactions"][0]
    assert "id" in tx
    assert "sender" in tx
    assert "receiver" in tx
    assert "payload" in tx

    # Non-existent height -> 404
    res_404 = client.get("/api/chain/99999")
    assert res_404.status_code == 404

    res_neg = client.get("/api/chain/-1")
    assert res_neg.status_code == 404


# ==============================================================================
# 6. Transaction Submission & Security (No Forgery Allowed)
# ==============================================================================

def test_transaction_submission_success(client):
    """
    Verify POST /api/transactions creates a valid cryptographically signed transaction.
    The node signs it with its internal private key. The caller cannot forge a signature.
    """
    res = client.post(
        "/api/transactions",
        json={"receiver": "orbital_depot_alpha", "amount": 5.0}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "submitted"
    assert data["amount"] == 5.0
    assert data["receiver"] == "orbital_depot_alpha"
    assert "tx_id" in data

    # Verify transaction entered node's mempool
    res_mempool = client.get("/api/mempool")
    assert res_mempool.status_code == 200
    mp_data = res_mempool.json()
    assert mp_data["count"] >= 1
    matching = [tx for tx in mp_data["transactions"] if tx["id"] == data["tx_id"]]
    assert len(matching) == 1

    # Cryptographically verify the signature created by the node's wallet
    signed_tx = matching[0]
    assert signed_tx["sign"] is not None
    vk = VerifyingKey.from_pem(signed_tx["sender"])
    sig_bytes = base64.b64decode(signed_tx["sign"])

    # Reconstruct transaction string representation
    reconstructed_tx = Transaction(
        signed_tx["payload"],
        signed_tx["sender"],
        signed_tx["receiver"],
        signed_tx["id"],
        signed_tx["timestamp"]
    )
    vk.verify(sig_bytes, str(reconstructed_tx).encode())


def test_transaction_submission_insufficient_balance(client):
    """Verify transaction submission is rejected when amount exceeds balance."""
    # Attempt to transfer 999999 coins
    res = client.post(
        "/api/transactions",
        json={"receiver": "orbital_depot_alpha", "amount": 999999.0}
    )
    assert res.status_code == 400
    assert "Insufficient balance" in res.json()["detail"]


def test_transaction_submission_malformed_inputs(client):
    """Verify validation rejection of malformed or invalid transaction inputs."""
    # 1. Negative amount
    res_neg = client.post(
        "/api/transactions",
        json={"receiver": "someone", "amount": -10.0}
    )
    assert res_neg.status_code == 422

    # 2. Zero amount
    res_zero = client.post(
        "/api/transactions",
        json={"receiver": "someone", "amount": 0.0}
    )
    assert res_zero.status_code == 422

    # 3. Empty receiver
    res_empty = client.post(
        "/api/transactions",
        json={"receiver": "", "amount": 5.0}
    )
    assert res_empty.status_code == 422

    # 4. Missing fields
    res_missing = client.post(
        "/api/transactions",
        json={"amount": 5.0}
    )
    assert res_missing.status_code == 422

    # 5. Non-numeric amount
    res_bad_type = client.post(
        "/api/transactions",
        json={"receiver": "someone", "amount": "five_hundred"}
    )
    assert res_bad_type.status_code == 422


# ==============================================================================
# 7. Unauthorized State Changes Forbidden (Consensus Integrity)
# ==============================================================================

def test_unauthorized_state_changes_rejected(client):
    """
    Verify API does not expose unauthorized mutation endpoints that could bypass consensus.
    Stakes and blocks can only be modified by the consensus state machine.
    """
    # 1. Modifying stakes via API is forbidden
    res_stake_post = client.post("/api/stakes", json={"amt": 100})
    assert res_stake_post.status_code in [404, 405]

    res_stake_put = client.put("/api/stakes", json={"amt": 100})
    assert res_stake_put.status_code in [404, 405]

    # 2. Modifying chain or injecting arbitrary blocks via API is forbidden
    res_chain_post = client.post("/api/chain", json={"block": {}})
    assert res_chain_post.status_code in [404, 405]

    res_chain_delete = client.delete("/api/chain/0")
    assert res_chain_delete.status_code in [404, 405]

    # 3. Deleting nodes is forbidden
    res_node_delete = client.delete("/api/nodes/test_vessel_1")
    assert res_node_delete.status_code in [404, 405]


# ==============================================================================
# 8. Stakes Telemetry (Read-Only)
# ==============================================================================

def test_stakes_endpoint_read_only(client):
    """Verify GET /api/stakes returns staking census without modifying consensus."""
    res = client.get("/api/stakes")
    assert res.status_code == 200
    data = res.json()
    assert "total_staked" in data
    assert "staker_count" in data
    assert "current_epoch_stakes" in data
    assert "node_is_staker" in data
    assert data["node_is_staker"] is True


# ==============================================================================
# 9. Consensus Status Telemetry
# ==============================================================================

def test_consensus_status_endpoint(client):
    """Verify GET /api/consensus/status exposes useful PoS metrics without secrets."""
    res = client.get("/api/consensus/status")
    assert res.status_code == 200
    data = res.json()
    assert data["consensus_type"] == "pos"
    assert "epoch_seed" in data
    assert "validator_count" in data
    assert "chain_length" in data
    assert data["chain_length"] >= 1
    assert "slashing_events" in data

    # Verify no private keys leaked
    raw_text = res.text
    assert "PRIVATE KEY" not in raw_text
    assert "private_key" not in raw_text


# ==============================================================================
# 10. Attack Surface Telemetry (Read-Only)
# ==============================================================================

def test_attack_telemetry_endpoint(client):
    """Verify GET /api/attacks/telemetry returns read-only monitoring records."""
    state = get_backend_state()
    # Simulate an incident recording
    state.record_fork(height=5, old_hash="OLD_HASH", new_hash="NEW_HASH", reason="Test fork")
    state.record_slashing(validator="MALICIOUS_VALIDATOR", reason="Double-signing equivocation", height=5)

    res = client.get("/api/attacks/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "monitoring"
    assert data["forks_detected"] >= 1
    assert data["slashing_incidents"] >= 1
    assert len(data["incidents"]) >= 2


# ==============================================================================
# 11. WebSocket Real-Time Event Streaming
# ==============================================================================

def test_websocket_stream_events(client):
    """
    Verify backend WebSocket stream connects, performs handshake,
    receives ping/pong, and streams live blockchain events.
    """
    with client.websocket_connect("/ws") as ws:
        # 1. Verify connection handshake envelope
        handshake = ws.receive_json()
        assert handshake["event"] == "connected"
        assert handshake["data"]["status"] == "Mission Control Status: Stellar"
        assert "supported_events" in handshake["data"]

        # 2. Verify ping / pong
        ws.send_json({"action": "ping"})
        pong = ws.receive_json()
        assert pong["event"] == "pong"
        assert pong["data"]["status"] == "Mission Control Status: Stellar"

        # 3. Trigger a transaction and verify event stream
        client.post(
            "/api/transactions",
            json={"receiver": "lunar_base_gamma", "amount": 3.0}
        )
        tx_event = ws.receive_json()
        assert tx_event["event"] == "transaction_received"
        assert tx_event["data"]["amount"] == 3.0
        assert tx_event["data"]["receiver"] == "lunar_base_gamma"


@pytest.mark.asyncio
async def test_websocket_broadcaster_all_event_types():
    """Verify EventBroadcaster handles all 9 core event types correctly."""
    from backend.events import EventBroadcaster
    broadcaster = EventBroadcaster()

    event_types = [
        "block_created",
        "block_received",
        "transaction_received",
        "validator_selected",
        "stake_added",
        "fork_detected",
        "validator_slashed",
        "peer_joined",
        "peer_left",
    ]

    for et in event_types:
        await broadcaster.broadcast_event(et, {"test_field": f"value_for_{et}"})

    history = broadcaster.get_recent_events(limit=50)
    assert len(history) == len(event_types)
    recorded_events = [h["event"] for h in history]
    assert recorded_events == event_types


def test_cosmo_polo_telemetry():
    """Verify required evaluation telemetry hook is preserved and reports Stellar."""
    assert cosmo_polo_telemetry() == "Mission Control Status: Stellar"

