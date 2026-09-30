"""
Deep-Space Mission Control — Backend Pydantic Schemas
=====================================================
Validated data transfer models for safe API serialization.
Strictly excludes all private keys, wallet secrets, and filesystem internals.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


# ==============================================================================
# 1. Network Models
# ==============================================================================

class NodeNetworkInfo(BaseModel):
    """Network presence record for an active constellation node."""
    node_id: str = Field(..., description="Unique node identity")
    name: str = Field(..., description="Display name of the node")
    host: str = Field(..., description="Network hostname or IP")
    port: int = Field(..., description="P2P WebSocket port")
    consensus: str = Field(..., description="Active consensus engine: pos, pow, or poa")
    status: str = Field(default="active", description="Node connection status")
    is_self: bool = Field(default=False, description="Whether this is the local host node")


class NetworkResponse(BaseModel):
    """Global network topology and discovery status."""
    room_id: Optional[str] = Field(None, description="Active discovery room / constellation sector ID")
    node_count: int = Field(..., description="Total active nodes discovered in network")
    nodes: List[NodeNetworkInfo] = Field(default_factory=list, description="List of connected nodes")
    consensus_types: List[str] = Field(default_factory=list, description="Consensus types present in sector")
    connection_status: str = Field(..., description="Signalling and P2P connection status")
    signalling_url: Optional[str] = Field(None, description="Signalling server rendezvous URL")
    is_standalone: bool = Field(default=False, description="True if operating in local observation mode")
    simulation_mode: str = Field(default="live", description="Simulation mode: live or standalone")



# ==============================================================================
# 2. Node Models
# ==============================================================================

class NodeDetailResponse(BaseModel):
    """Safe, non-confidential node telemetry and identity details."""
    node_id: str = Field(..., description="Unique node identity")
    name: str = Field(..., description="Node name")
    public_key: str = Field(..., description="Public key (PEM or fingerprint). Secrets are never exposed.")
    consensus: str = Field(..., description="Active consensus engine")
    host: str = Field(..., description="Host IP")
    port: int = Field(..., description="P2P Port")
    status: str = Field(default="active", description="Operational status: active, staker, miner, etc.")
    balance: Optional[float] = Field(None, description="Calculated account balance from blockchain")
    is_self: bool = Field(default=False, description="Whether this node is the local node")
    staked_amount: Optional[int] = Field(None, description="Current staked amount if PoS validator")
    peer_count: Optional[int] = Field(None, description="Number of direct P2P connections")


class NodeListResponse(BaseModel):
    """Census of all known nodes in the simulation."""
    total: int
    nodes: List[NodeDetailResponse]


# ==============================================================================
# 3. Blockchain & Block Models
# ==============================================================================

class TransactionSummary(BaseModel):
    """Serialized blockchain transaction details."""
    id: str
    sender: str
    receiver: str
    payload: Any
    timestamp: Any
    sign: Optional[str] = None


class PoSBlockMetadata(BaseModel):
    """Consensus telemetry specific to Proof-of-Stake blocks."""
    seed: Optional[str] = None
    vrf_proof_b64: Optional[str] = None
    staked_amt: Optional[int] = None
    stakers_count: Optional[int] = None
    stakers: Optional[List[Dict[str, Any]]] = None
    slash_creator: Optional[bool] = False


class BlockSummary(BaseModel):
    """Safe summary of a mined or forged block."""
    height: int = Field(..., description="Block index in the chain")
    hash: str = Field(..., description="Cryptographic SHA-256 block hash")
    previous_hash: Optional[str] = Field(None, description="Parent block hash")
    creator: str = Field(..., description="Block creator / miner identity")
    timestamp: Any = Field(..., description="Block generation timestamp")
    transaction_count: int = Field(..., description="Number of confirmed transactions")
    consensus_type: str = Field(..., description="Consensus engine of block: pos, pow, poa")
    pos_metadata: Optional[PoSBlockMetadata] = None


class BlockDetail(BaseModel):
    """Comprehensive details of a confirmed block."""
    height: int
    id: str
    hash: str
    previous_hash: Optional[str] = None
    creator: str
    timestamp: Any
    transactions: List[TransactionSummary] = Field(default_factory=list)
    transaction_count: int
    consensus_type: str
    pos_metadata: Optional[PoSBlockMetadata] = None
    files: Optional[Dict[str, str]] = None


class ChainResponse(BaseModel):
    """Blockchain overview and serialized block list."""
    length: int
    chain: List[BlockSummary]


# ==============================================================================
# 4. Transaction Submission Models
# ==============================================================================

class TransactionCreateRequest(BaseModel):
    """Request payload to create a new transaction using the node's secure wallet."""
    receiver: str = Field(..., min_length=1, description="Recipient public key PEM or recipient directory name")
    amount: float = Field(..., gt=0, description="Amount of coins to transfer (must be strictly positive)")


class TransactionResponse(BaseModel):
    """Confirmation of an accepted and broadcast transaction."""
    status: str = "submitted"
    tx_id: str
    sender: str
    receiver: str
    amount: float
    timestamp: Any


class TransactionListResponse(BaseModel):
    """List of confirmed transactions recorded in the blockchain."""
    total: int
    transactions: List[TransactionSummary]


# ==============================================================================
# 5. Mempool Models
# ==============================================================================

class MempoolResponse(BaseModel):
    """Real-time transaction pool awaiting block confirmation."""
    count: int
    transactions: List[TransactionSummary]


# ==============================================================================
# 6. Stakes Models
# ==============================================================================

class StakeInfo(BaseModel):
    """PoS validator stake record."""
    id: str
    staker: str
    amt: int
    timestamp: Any
    sign: Optional[str] = None


class StakesResponse(BaseModel):
    """Read-only PoS staking census. State modifications are forbidden."""
    total_staked: int
    staker_count: int
    current_epoch_stakes: List[StakeInfo]
    node_is_staker: bool
    node_staked_amt: int
    epoch_remaining_seconds: Optional[float] = None


# ==============================================================================
# 7. Consensus Models
# ==============================================================================

class ConsensusStatusResponse(BaseModel):
    """Consensus state machine telemetry."""
    consensus_type: str
    epoch_seed: Optional[str] = None
    validators: List[Dict[str, Any]] = Field(default_factory=list)
    validator_count: int = 0
    total_stake: int = 0
    eligibility_status: Optional[bool] = None
    latest_block: Optional[BlockSummary] = None
    chain_length: int = 0
    chain_weight: Optional[float] = None
    slashing_events: List[Dict[str, Any]] = Field(default_factory=list)


# ==============================================================================
# 8. Attacks Telemetry Models
# ==============================================================================

class AttackTelemetryResponse(BaseModel):
    """Read-only attack telemetry monitoring for attack lab visualization."""
    status: str = "monitoring"
    forks_detected: int = 0
    slashing_incidents: int = 0
    invalid_blocks_rejected: int = 0
    double_sign_attempts: int = 0
    malicious_peers_detected: List[str] = Field(default_factory=list)
    incidents: List[Dict[str, Any]] = Field(default_factory=list)


class AttackExecutionRequest(BaseModel):
    """Parameters for executing a sandboxed attack simulation."""
    target_node: Optional[str] = None
    malicious_validator: Optional[str] = None
    amount: Optional[float] = None
    custom_params: Optional[Dict[str, Any]] = None


class AttackTimelineEvent(BaseModel):
    """Single stage timestamped record in an attack lifecycle."""
    timestamp: float
    time_str: str
    stage: str  # READY, ARMED, EXECUTING, DETECTED, MITIGATED, REJECTED, COMPLETE
    message: str


class AttackExecutionResponse(BaseModel):
    """Structured result of an executed sandbox attack scenario."""
    attack_id: str
    attack_type: str
    status: str  # ready, armed, executing, detected, mitigated, rejected, complete
    target: str
    is_sandboxed: bool = True
    evidence: Dict[str, Any] = Field(default_factory=dict)
    network_response: str
    timeline: List[AttackTimelineEvent] = Field(default_factory=list)
    final_state: Dict[str, Any] = Field(default_factory=dict)


class AttackScenarioInfo(BaseModel):
    """Metadata describing a supported attack scenario."""
    id: str
    name: str
    description: str
    supported_consensus: List[str]
    parameters: List[str]
    expected_outcome: str


class AttackScenarioListResponse(BaseModel):
    """Census of all available sandboxed attack scenarios."""
    scenarios: List[AttackScenarioInfo]
    sandbox_status: str = "LOCAL_SANDBOX_ENFORCED"


# ==============================================================================
# 9. WebSocket Event Models
# ==============================================================================

class WebSocketEvent(BaseModel):
    """Structured real-time event envelope emitted to dashboard clients."""
    event: str = Field(..., description="Event name: block_created, transaction_received, etc.")
    timestamp: float = Field(..., description="UNIX epoch timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")


# ==============================================================================
# 10. Phase 8 Metrics & Telemetry Models
# ==============================================================================

class MetricPointModel(BaseModel):
    """Timestamped observational data point for timeseries charts."""
    timestamp: float
    value: float


class NetworkMetricsResponse(BaseModel):
    """Observational Network telemetry."""
    active_nodes: int
    known_peers: int
    connected_peers: int
    peer_joins_total: int
    peer_leaves_total: int
    history_peer_count: List[MetricPointModel] = Field(default_factory=list)
    is_standalone: bool = True
    simulation_mode: str = "standalone"


class BlockchainMetricsResponse(BaseModel):
    """Observational Blockchain production & block rate telemetry."""
    block_height: int
    total_blocks_observed: int
    blocks_created: int
    blocks_received: int
    latest_block_timestamp: Optional[float] = None
    latest_block_interval_seconds: Optional[float] = None
    average_block_interval_seconds: Optional[float] = None
    blocks_per_minute: Optional[float] = None
    history_block_intervals: List[MetricPointModel] = Field(default_factory=list)
    history_blocks_per_minute: List[MetricPointModel] = Field(default_factory=list)
    forks_detected_total: int = 0
    canonical_chain_reorgs_total: int = 0


class TransactionMetricsResponse(BaseModel):
    """Observational Transaction pipeline & authentic throughput telemetry."""
    transactions_submitted: int
    transactions_accepted: int
    transactions_rejected: int
    transactions_confirmed: int
    current_tps: Optional[float] = 0.0
    history_tps: List[MetricPointModel] = Field(default_factory=list)
    confirmation_latency_avg_seconds: Optional[float] = None


class MempoolMetricsResponse(BaseModel):
    """Observational Mempool depth and historical trajectory."""
    current_mempool_size: int
    transactions_entered_mempool_total: int
    transactions_exited_mempool_total: int
    history_mempool_depth: List[MetricPointModel] = Field(default_factory=list)


class ConsensusMetricsResponse(BaseModel):
    """Consensus-aware telemetry across PoS, PoW, and PoA."""
    consensus_type: str
    available: bool = True
    pos: Optional[Dict[str, Any]] = None
    pow: Optional[Dict[str, Any]] = None
    poa: Optional[Dict[str, Any]] = None


class SecurityMetricsResponse(BaseModel):
    """Aggregated security events and Phase 7 Attack Lab telemetry."""
    total_attack_attempts: int = 0
    attacks_by_type: Dict[str, int] = Field(default_factory=dict)
    detected_attacks: int = 0
    rejected_attacks: int = 0
    mitigated_attacks: int = 0
    completed_attacks: int = 0
    detection_rate_pct: Optional[float] = None
    mitigation_rate_pct: Optional[float] = None
    canonical_chain_preserved_count: int = 0
    recent_security_incidents: List[Dict[str, Any]] = Field(default_factory=list)


class MetricsSummaryKPIs(BaseModel):
    """High-level summary KPI metrics for rapid monitoring."""
    block_height: int
    current_tps: Optional[float] = 0.0
    mempool_depth: int
    active_nodes: int
    peer_count: int
    consensus_type: str
    average_block_interval_seconds: Optional[float] = None
    total_attacks: int = 0
    mitigation_rate_pct: Optional[float] = None


class MetricsOverviewResponse(BaseModel):
    """Consolidated system observability report across all simulation vectors."""
    status: str = "online"
    telemetry: str = "Mission Control Status: Stellar"
    timestamp: float
    is_standalone: bool
    simulation_mode: str
    summary_kpis: MetricsSummaryKPIs
    network: NetworkMetricsResponse
    blockchain: BlockchainMetricsResponse
    transactions: TransactionMetricsResponse
    mempool: MempoolMetricsResponse
    consensus: ConsensusMetricsResponse
    security: SecurityMetricsResponse


class MetricsResetResponse(BaseModel):
    """Confirmation of telemetry-only sliding history and counter reset."""
    status: str = "reset_complete"
    message: str
    timestamp: float
