"""
Deep-Space Mission Control — Phase 8 Metrics & Telemetry Test Suite
===================================================================
Comprehensive unit, regression, integration, and security verification:
- Initial empty states & unavailable metrics handling
- Authentic rate calculations (TPS, block interval, blocks/min)
- Robust edge cases: zero events, single events, identical & out-of-order timestamps
- Bounded memory buffer eviction (deque maxlen enforcement)
- Consensus-specific metrics (PoS, PoW, PoA)
- Security & Phase 7 Attack Lab telemetry integration
- Telemetry reset isolation (canonical state preservation)
- Zero private key / secret material leakage
- REST endpoint availability and schema conformity

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import time
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app, cosmo_polo_telemetry
from backend.state import SimulationBackendState
from backend.metrics import BlockchainMetricsCollector, MetricPoint
from backend.models import (
    MetricsOverviewResponse,
    NetworkMetricsResponse,
    BlockchainMetricsResponse,
    TransactionMetricsResponse,
    MempoolMetricsResponse,
    ConsensusMetricsResponse,
    SecurityMetricsResponse,
)
from shared_blockchain_structures import Wallet


def test_cosmo_polo_telemetry():
    """Verifies the mandatory Mission Control telemetry hook."""
    assert cosmo_polo_telemetry() == "Mission Control Status: Stellar"


class MockBlock:
    """Mock block object for authentic delta testing."""
    def __init__(self, height: int, ts: float, txs=None, creator="validator_alpha", seed="seed_001"):
        self.height = height
        self.ts = ts
        self.transactions = txs or []
        self.creator = creator
        self.seed = seed
        self.prevHash = "PREV_HASH"
        self.hash = f"HASH_{height}"


class MockTx:
    """Mock transaction object for latency testing."""
    def __init__(self, tx_id: str, ts: float):
        self.id = tx_id
        self.ts = ts


def test_initial_empty_state_and_unavailable_metrics():
    """
    Verifies that fresh metrics collector initializes cleanly with valid defaults
    and explicit None / unavailable states rather than fabricated numbers.
    """
    state = SimulationBackendState()
    collector = BlockchainMetricsCollector(state, max_history=10)

    # Empty blockchain: < 2 blocks means interval is None
    bc = collector.get_blockchain_metrics()
    assert bc["block_height"] >= 0
    assert bc["latest_block_interval_seconds"] is None
    assert bc["average_block_interval_seconds"] is None

    # Empty transactions: 0 tps
    tx = collector.get_transaction_metrics()
    assert tx["transactions_submitted"] == 0
    assert tx["current_tps"] == 0.0
    assert tx["confirmation_latency_avg_seconds"] is None

    # Empty attacks: detection rate is None (cannot divide by 0)
    sec = collector.get_security_metrics()
    assert sec["total_attack_attempts"] == 0
    assert sec["detection_rate_pct"] is None
    assert sec["mitigation_rate_pct"] is None


def test_block_interval_and_rate_calculations():
    """
    Verifies authentic block interval calculation across multiple consecutive blocks.
    """
    state = SimulationBackendState()
    collector = BlockchainMetricsCollector(state, max_history=10)

    t0 = 1000.0
    b0 = MockBlock(height=0, ts=t0)
    b1 = MockBlock(height=1, ts=t0 + 10.0)
    b2 = MockBlock(height=2, ts=t0 + 25.0)

    collector.record_block(b0)
    collector.record_block(b1)
    collector.record_block(b2)

    # Intervals: (b1-b0 = 10s), (b2-b1 = 15s) -> average = 12.5s
    intervals = [p.value for p in collector.history_block_intervals]
    assert len(intervals) == 2
    assert intervals[0] == 10.0
    assert intervals[1] == 15.0


def test_edge_case_single_block():
    """
    With only 1 block, block interval cannot legitimately be computed. Must return None.
    """
    state = SimulationBackendState()
    collector = BlockchainMetricsCollector(state, max_history=10)

    collector.record_block(MockBlock(height=0, ts=500.0))
    assert len(collector.history_block_intervals) == 0


def test_edge_case_identical_and_out_of_order_timestamps():
    """
    Ensures identical or out-of-order timestamps do not crash the metrics engine.
    """
    state = SimulationBackendState()
    collector = BlockchainMetricsCollector(state, max_history=10)

    # Identical timestamps: delta = 0
    collector.record_block(MockBlock(height=0, ts=100.0))
    collector.record_block(MockBlock(height=1, ts=100.0))
    assert collector.history_block_intervals[-1].value == 0.0

    # Clock skew / out-of-order: uses abs() delta
    collector.record_block(MockBlock(height=2, ts=95.0))
    assert collector.history_block_intervals[-1].value == 5.0


def test_authentic_tps_calculation():
    """
    Verifies that TPS is derived strictly from confirmed transaction events over real time window.
    """
    state = SimulationBackendState()
    collector = BlockchainMetricsCollector(state, max_history=10)

    now = time.time()
    # Confirm 20 transactions in sliding 10s window -> TPS = 2.0
    collector.record_transactions_confirmed(count=20)
    collector.record_sample(timestamp=now)

    tx_metrics = collector.get_transaction_metrics()
    assert tx_metrics["transactions_confirmed"] >= 20
    assert tx_metrics["current_tps"] == 2.0


def test_confirmation_latency_tracking():
    """
    Verifies average confirmation latency calculation when tx and block timestamps exist.
    """
    state = SimulationBackendState()
    collector = BlockchainMetricsCollector(state, max_history=10)

    tx1 = MockTx("tx1", ts=100.0)
    tx2 = MockTx("tx2", ts=102.0)
    # Confirmed in block at ts=106.0 -> latencies: (106-100=6s), (106-102=4s) -> avg = 5.0s
    collector.record_transactions_confirmed(count=2, block_ts=106.0, tx_list=[tx1, tx2])

    tx_metrics = collector.get_transaction_metrics()
    assert tx_metrics["confirmation_latency_avg_seconds"] == 5.0


def test_bounded_history_eviction():
    """
    Verifies that circular buffers enforce maxlen and prevent unbounded memory growth.
    """
    state = SimulationBackendState()
    limit = 5
    collector = BlockchainMetricsCollector(state, max_history=limit)

    for i in range(20):
        collector.record_sample(timestamp=1000.0 + i)

    assert len(collector.history_peer_count) <= limit
    assert len(collector.history_mempool_depth) <= limit
    assert len(collector.history_tps) <= limit
    assert len(collector.history_blocks_per_minute) <= limit


def test_security_and_attack_metrics_integration():
    """
    Verifies integration with Phase 7 Attack Lab lifecycle transitions.
    """
    state = SimulationBackendState()
    collector = BlockchainMetricsCollector(state, max_history=10)

    # 1. Execute double_sign: started -> detected -> mitigated
    collector.record_attack_lifecycle("double_sign", "started")
    collector.record_attack_lifecycle("double_sign", "detected")
    collector.record_attack_lifecycle("double_sign", "mitigated")

    # 2. Execute double_spend: started -> detected -> rejected
    collector.record_attack_lifecycle("double_spend", "started")
    collector.record_attack_lifecycle("double_spend", "detected")
    collector.record_attack_lifecycle("double_spend", "rejected")

    sec = collector.get_security_metrics()
    assert sec["total_attack_attempts"] == 2
    assert sec["attacks_by_type"]["double_sign"] == 1
    assert sec["attacks_by_type"]["double_spend"] == 1
    assert sec["detected_attacks"] == 2
    assert sec["mitigated_attacks"] == 1
    assert sec["rejected_attacks"] == 1
    assert sec["detection_rate_pct"] == 100.0
    assert sec["mitigation_rate_pct"] == 50.0
    assert sec["canonical_chain_preserved_count"] == 2
    assert len(sec["recent_security_incidents"]) == 6


def test_telemetry_reset_isolation():
    """
    Verifies that resetting metrics clears telemetry buffers without altering
    canonical chain blocks or consensus state.
    """
    state = SimulationBackendState()
    collector = BlockchainMetricsCollector(state, max_history=10)

    # Add telemetry data
    collector.record_block(MockBlock(0, 100.0))
    collector.record_block(MockBlock(1, 110.0))
    collector.record_transaction_submitted()
    collector.record_attack_lifecycle("fork", "started")

    # Reset
    res = collector.reset_metrics()
    assert res["status"] == "reset_complete"
    assert collector.total_attack_attempts == 0
    assert collector.transactions_submitted_total == 0
    assert len(collector.history_block_intervals) == 0

    # Ensure underlying chain was NOT deleted
    assert state.get_blocks() is not None


def test_no_private_keys_in_metrics_serialization():
    """
    Security check: Verifies that serialized metrics output never contains private keys.
    """
    state = SimulationBackendState()
    wallet = Wallet()
    priv_pem = wallet.private_key_pem

    overview = state.metrics.get_overview_metrics()
    overview_str = str(overview)

    assert "BEGIN EC PRIVATE KEY" not in overview_str
    assert "BEGIN PRIVATE KEY" not in overview_str
    assert priv_pem not in overview_str


# ==============================================================================
# REST API Endpoint Tests
# ==============================================================================

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_api_metrics_overview(client):
    """Tests GET /api/metrics consolidated endpoint."""
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "online"
    assert data["telemetry"] == "Mission Control Status: Stellar"
    assert "summary_kpis" in data
    assert "network" in data
    assert "blockchain" in data
    assert "transactions" in data
    assert "mempool" in data
    assert "consensus" in data
    assert "security" in data


def test_api_metrics_subsystem_endpoints(client):
    """Tests granular GET /api/metrics/* subsystem endpoints."""
    r_net = client.get("/api/metrics/network")
    assert r_net.status_code == 200
    assert "active_nodes" in r_net.json()

    r_bc = client.get("/api/metrics/blockchain")
    assert r_bc.status_code == 200
    assert "block_height" in r_bc.json()

    r_tx = client.get("/api/metrics/transactions")
    assert r_tx.status_code == 200
    assert "current_tps" in r_tx.json()

    r_mem = client.get("/api/metrics/mempool")
    assert r_mem.status_code == 200
    assert "current_mempool_size" in r_mem.json()

    r_cs = client.get("/api/metrics/consensus")
    assert r_cs.status_code == 200
    assert "consensus_type" in r_cs.json()

    r_sec = client.get("/api/metrics/security")
    assert r_sec.status_code == 200
    assert "total_attack_attempts" in r_sec.json()


def test_api_metrics_reset(client):
    """Tests POST /api/metrics/reset endpoint."""
    res = client.post("/api/metrics/reset")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "reset_complete"
