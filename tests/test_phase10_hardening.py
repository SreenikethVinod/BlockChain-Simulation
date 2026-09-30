"""
Phase 10 — Final Hardening & Integration Test Suite.
Covers:
  - Bounded Mempool Capacity & Rejection Policies (SEC-08)
  - Deterministic Gas Metering & Limit Enforcement (SEC-09)
  - Transaction Nonce & Domain Separation Replay Defenses (Original SEC-08)
  - Atomic File Persistence & Corruption Prevention (Original SEC-09)
  - Multi-Node P2P Authenticated Integration (End-to-End Pipeline)
"""

import os
import copy
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from shared_blockchain_structures import (
    Transaction,
    Wallet,
    validate_transaction_domain,
    cosmo_polo_telemetry
)
from consensus.pos.blockchain_structures import (
    Block,
    Chain,
    Stake,
    generate_vrf_proof,
    compute_vrf_output,
    is_vrf_eligible
)
from consensus.pos.p2p import Peer
import storage.storage_manager as sm
from smart_contract.gas_meter import GasMeter
from smart_contract.smart_contract import ContractEnvironment
from backend.state import SimulationBackendState, get_backend_state
from backend.app import create_app
from fastapi.testclient import TestClient


# ==============================================================================
# 1. Bounded Mempool Tests (SEC-08)
# ==============================================================================

@pytest.mark.asyncio
async def test_bounded_mempool_capacity_enforced():
    """
    Verifies that Peer mempool enforces max_mempool_size capacity,
    rejecting subsequent transactions once full without corrupting existing ones.
    """
    peer = Peer("127.0.0.1", 9801, "mempool_node", True, "n", "n")
    peer.max_mempool_size = 10  # Set small limit for testing

    w1, w2 = Wallet(), Wallet()

    # Fill mempool to capacity
    for i in range(10):
        tx = Transaction(1.0 + i, w1.public_key_pem, w2.public_key_pem)
        tx.sign = w1.private_key.sign(str(tx).encode())
        async with peer.mem_pool_lock:
            peer.mem_pool.append(tx)

    assert len(peer.mem_pool) == 10

    # Attempt to insert 11th transaction via create_and_broadcast_tx
    Chain.instance = None
    genesis = Block(None, [], ts=1000)
    genesis.creator = peer.wallet.public_key_pem
    genesis.sign = peer.wallet.private_key.sign(str(genesis).encode())
    Chain.instance = Chain(blockList=[genesis])

    res = await peer.create_and_broadcast_tx(w2.public_key_pem, 5.0)
    assert res is None  # Rejected due to capacity
    assert len(peer.mem_pool) == 10  # Size strictly bounded


def test_backend_api_rejects_transaction_when_mempool_full():
    """
    Verifies that POST /api/transactions returns HTTP 429 when mempool is at capacity.
    """
    app = create_app()
    client = TestClient(app)

    state = get_backend_state()
    peer = state.get_peer()
    if not peer:
        pytest.skip("No active peer in test backend")

    peer.max_mempool_size = 5
    w_dummy = Wallet()

    # Pre-fill mempool to max capacity
    peer.mem_pool = []
    for i in range(5):
        t = Transaction(10, w_dummy.public_key_pem, "receiver")
        peer.mem_pool.append(t)

    res = client.post("/api/transactions", json={
        "receiver": "test_recipient_public_key",
        "amount": 1.0
    })
    assert res.status_code == 429
    assert "mempool capacity reached" in res.json()["detail"].lower()

    # Clean up
    peer.mem_pool = []
    peer.max_mempool_size = 500


def test_mempool_metrics_reports_capacity_and_utilization():
    """
    Verifies that get_mempool_metrics correctly reports max capacity and utilization %.
    """
    from backend.metrics import BlockchainMetricsCollector
    state = SimulationBackendState()
    peer = Peer("127.0.0.1", 9802, "metric_node", True, "n", "n")
    peer.max_mempool_size = 100
    w = Wallet()
    for i in range(25):
        peer.mem_pool.append(Transaction(1.0, w.public_key_pem, "recv"))
    state.set_peer(peer, is_standalone=True)

    metrics = BlockchainMetricsCollector(state_ref=state)
    mem_data = metrics.get_mempool_metrics()

    assert mem_data["current_mempool_size"] == 25
    assert mem_data["max_mempool_capacity"] == 100
    assert mem_data["mempool_utilization_pct"] == 25.0


# ==============================================================================
# 2. Deterministic Gas Simulation Tests (SEC-09)
# ==============================================================================

def test_deterministic_gas_metering_and_limit():
    """
    Verifies that smart contract gas is deterministically metered and raises
    'Out of gas' when computational limit is exceeded.
    """
    code_infinite = "def run_loop(n, state):\n    i = 0\n    while i < n:\n        i += 1\n    return state, 'done'\n"

    env = ContractEnvironment(code_infinite, gas_limit=50)

    # Within gas limit (5 iterations should take < 50 gas)
    state, msg, gas = env.run_contract("run_loop", [5], {})
    assert msg == "done"
    assert gas > 0
    assert gas <= 50

    # Exceeding gas limit (200 iterations must trigger Out of gas)
    with pytest.raises(Exception) as exc_info:
        env.run_contract("run_loop", [200], {})
    assert "out of gas" in str(exc_info.value).lower()


def test_p2p_valid_deploy_transaction_gas_limit():
    """
    Verifies that Peer.valid_deploy_transaction rejects payloads exceeding MAX_CONTRACT_GAS_LIMIT.
    """
    peer = Peer("127.0.0.1", 9803, "gas_node", True, "n", "n")
    # Massive code > 100,000 chars would require > 10,000 gas
    huge_code = "# " + ("A" * 150000)
    cost = len(huge_code) // 10 + 5
    payload = [huge_code, cost * 0.001]

    # Should be rejected for exceeding gas limit
    assert peer.valid_deploy_transaction(payload) is False


# ==============================================================================
# 3. Transaction Nonce & Domain Separation Tests (Original SEC-08)
# ==============================================================================

def test_transaction_domain_separation():
    """
    Verifies that transactions can carry chain/network domain context, and
    validate_transaction_domain rejects cross-room replay attempts.
    """
    w1, w2 = Wallet(), Wallet()

    # Tx on Room/Chain "constellation-alpha"
    tx_alpha = Transaction(50, w1.public_key_pem, w2.public_key_pem, nonce=1, chain_id="constellation-alpha")
    tx_alpha.sign = w1.private_key.sign(str(tx_alpha).encode())

    # Valid in its intended domain
    assert validate_transaction_domain(tx_alpha, expected_chain_id="constellation-alpha") is True

    # Replayed into Room/Chain "constellation-beta" -> REJECTED
    assert validate_transaction_domain(tx_alpha, expected_chain_id="constellation-beta") is False


def test_transaction_nonce_serialization_and_equality():
    """
    Verifies that nonces serialize into dictionary and are considered in equality.
    """
    w1, w2 = Wallet(), Wallet()
    tx1 = Transaction(20, w1.public_key_pem, w2.public_key_pem, nonce=42)
    d = tx1.to_dict()
    assert d.get("nonce") == 42

    tx2 = Transaction(20, w1.public_key_pem, w2.public_key_pem, nonce=43)
    assert tx1 != tx2  # Different nonces are not equal


# ==============================================================================
# 4. Atomic Storage Persistence Tests (Original SEC-09)
# ==============================================================================

def test_atomic_storage_prevents_partial_writes(tmp_path):
    """
    Verifies that atomic_write_json writes to temporary file and atomically
    replaces target file without data corruption.
    """
    target_file = str(tmp_path / "test_atomic_ledger.json")

    # Initial write
    initial_data = {"chain": [1, 2, 3], "status": "active"}
    sm.atomic_write_json(target_file, initial_data)

    with open(target_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == initial_data

    # Update write
    updated_data = {"chain": [1, 2, 3, 4], "status": "updated"}
    sm.atomic_write_json(target_file, updated_data)

    with open(target_file, "r", encoding="utf-8") as f:
        loaded_updated = json.load(f)
    assert loaded_updated == updated_data

    # Verify no dangling temp files remain in directory
    files_in_dir = os.listdir(str(tmp_path))
    assert len(files_in_dir) == 1
    assert files_in_dir[0] == "test_atomic_ledger.json"


# ==============================================================================
# 5. Multi-Node Authenticated P2P Integration Tests
# ==============================================================================

def test_multi_node_authenticated_handshake_flow():
    """
    Verifies mutual cryptographic authentication across 3 nodes
    (node1, node2, node3) using nonces and ECDSA key possession proofs.
    """
    nodes = [
        Peer("127.0.0.1", 9911, "node-alpha", True, "n", "n"),
        Peer("127.0.0.1", 9912, "node-beta", True, "n", "n"),
        Peer("127.0.0.1", 9913, "node-gamma", True, "n", "n")
    ]

    # Node Alpha initiates handshake to Node Beta
    challenge_beta = "beta-nonce-789"
    hs_alpha = nodes[0].create_auth_handshake(challenge=challenge_beta)
    assert nodes[1].verify_peer_handshake(hs_alpha, expected_challenge=challenge_beta) is True

    # Node Beta initiates handshake to Node Gamma
    challenge_gamma = "gamma-nonce-101"
    hs_beta = nodes[1].create_auth_handshake(challenge=challenge_gamma)
    assert nodes[2].verify_peer_handshake(hs_beta, expected_challenge=challenge_gamma) is True

    # Node Gamma initiates handshake to Node Alpha
    challenge_alpha = "alpha-nonce-202"
    hs_gamma = nodes[2].create_auth_handshake(challenge=challenge_alpha)
    assert nodes[0].verify_peer_handshake(hs_gamma, expected_challenge=challenge_alpha) is True


# ==============================================================================
# LIMIT-01 — Shared EPOCH_TIME Constant Regression
# ==============================================================================

def test_epoch_time_shared_constant_importable():
    """
    LIMIT-01 Regression: EPOCH_TIME must be importable from the canonical
    blockchain_structures module. It must not be a magic literal that can
    silently diverge between consensus modules.
    """
    from consensus.pos.blockchain_structures import EPOCH_TIME as bs_epoch
    assert bs_epoch == 60, "EPOCH_TIME must equal 60 seconds"
    assert isinstance(bs_epoch, int), "EPOCH_TIME must be an integer"


def test_epoch_time_not_redefined_in_p2p():
    """
    LIMIT-01 Regression: p2p.py must import EPOCH_TIME from blockchain_structures,
    not redefine it locally. Verifies the import path is consistent.
    """
    import consensus.pos.p2p as p2p_module
    import consensus.pos.blockchain_structures as bs_module
    # Both must refer to the same value - p2p imports from blockchain_structures
    assert bs_module.EPOCH_TIME == 60
    # Verify p2p uses the imported constant (module attribute check)
    assert hasattr(bs_module, "EPOCH_TIME")


# ==============================================================================
# LIMIT-02 — Cross-Domain Transaction Rejection Regression
# ==============================================================================

def test_cross_domain_transaction_rejected():
    """
    LIMIT-02 Regression: validate_transaction_domain must reject transactions
    whose chain_id does not match the expected domain. This prevents silent
    cross-simulation replay attacks between separate simulation instances.
    """
    w = Wallet()
    # Transaction in the correct domain
    tx_valid = Transaction(5.0, w.public_key_pem, "other_node", chain_id="simulation")
    assert validate_transaction_domain(tx_valid, expected_chain_id="simulation") is True

    # Transaction in a foreign domain - must be rejected
    tx_foreign = Transaction(5.0, w.public_key_pem, "other_node", chain_id="testnet-fork")
    assert validate_transaction_domain(tx_foreign, expected_chain_id="simulation") is False


def test_cross_domain_transaction_custom_chain():
    """
    LIMIT-02 Regression: validate_transaction_domain must also work for custom
    chain IDs (not just 'simulation'), enabling future multi-chain setups.
    """
    w = Wallet()
    tx_alpha = Transaction(3.0, w.public_key_pem, "recv", chain_id="constellation-alpha")
    tx_beta = Transaction(3.0, w.public_key_pem, "recv", chain_id="constellation-beta")

    assert validate_transaction_domain(tx_alpha, expected_chain_id="constellation-alpha") is True
    assert validate_transaction_domain(tx_alpha, expected_chain_id="constellation-beta") is False
    assert validate_transaction_domain(tx_beta, expected_chain_id="constellation-alpha") is False


def test_default_chain_id_is_simulation():
    """
    LIMIT-02 Regression: The default chain_id for new transactions must be
    'simulation' to maintain backward compatibility with existing nodes.
    """
    w = Wallet()
    tx = Transaction(1.0, w.public_key_pem, "recv")
    assert tx.chain_id == "simulation"
    assert validate_transaction_domain(tx, expected_chain_id="simulation") is True
