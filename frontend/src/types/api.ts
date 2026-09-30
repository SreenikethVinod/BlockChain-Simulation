/**
 * Deep-Space Mission Control — Frontend Type Definitions
 * Directly aligned with Phase 5 FastAPI backend response contracts.
 */

export interface NodeNetworkInfo {
  node_id: string;
  name: string;
  host: string;
  port: number;
  consensus: string;
  status: string;
  is_self: boolean;
}

export interface NetworkResponse {
  room_id: string | null;
  node_count: number;
  nodes: NodeNetworkInfo[];
  consensus_types: string[];
  connection_status: string;
  signalling_url: string | null;
  is_standalone: boolean;
  simulation_mode: 'live' | 'standalone' | string;
}

export interface NodeDetailResponse {
  node_id: string;
  name: string;
  public_key: string;
  consensus: string;
  host: string;
  port: number;
  status: string;
  balance: number | null;
  is_self: boolean;
  staked_amount?: number | null;
  peer_count?: number | null;
}

export interface NodeListResponse {
  total: number;
  nodes: NodeDetailResponse[];
}

export interface TransactionSummary {
  id: string;
  sender: string;
  receiver: string;
  payload: any;
  timestamp: any;
  sign?: string | null;
}

export interface PoSBlockMetadata {
  seed?: string | null;
  vrf_proof_b64?: string | null;
  staked_amt?: number | null;
  stakers_count?: number | null;
  stakers?: Array<{ staker: string; amt: number }> | null;
  slash_creator?: boolean;
}

export interface BlockSummary {
  height: number;
  hash: string;
  previous_hash: string | null;
  creator: string;
  timestamp: any;
  transaction_count: number;
  consensus_type: string;
  pos_metadata?: PoSBlockMetadata | null;
}

export interface BlockDetail {
  height: number;
  id: string;
  hash: string;
  previous_hash: string | null;
  creator: string;
  timestamp: any;
  transactions: TransactionSummary[];
  transaction_count: number;
  consensus_type: string;
  pos_metadata?: PoSBlockMetadata | null;
  files?: Record<string, string> | null;
}

export interface ChainResponse {
  length: number;
  chain: BlockSummary[];
}

export interface TransactionCreateRequest {
  receiver: string;
  amount: number;
}

export interface TransactionResponse {
  status: string;
  tx_id: string;
  sender: string;
  receiver: string;
  amount: number;
  timestamp: any;
}

export interface TransactionListResponse {
  total: number;
  transactions: TransactionSummary[];
}

export interface MempoolResponse {
  count: number;
  transactions: TransactionSummary[];
}

export interface StakeInfo {
  id: string;
  staker: string;
  amt: number;
  timestamp: any;
  sign?: string | null;
}

export interface StakesResponse {
  total_staked: number;
  staker_count: number;
  current_epoch_stakes: StakeInfo[];
  node_is_staker: boolean;
  node_staked_amt: number;
  epoch_remaining_seconds?: number | null;
}

export interface ValidatorEntry {
  staker: string;
  staked_amount: number;
  is_local?: boolean;
}

export interface ConsensusStatusResponse {
  consensus_type: string;
  epoch_seed: string | null;
  validators: ValidatorEntry[];
  validator_count: number;
  total_stake: number;
  eligibility_status: boolean | null;
  latest_block: BlockSummary | null;
  chain_length: number;
  chain_weight: number | null;
  slashing_events: Array<Record<string, any>>;
}

export interface AttackIncident {
  type: string;
  time: number;
  [key: string]: any;
}

export interface AttackTelemetryResponse {
  status: string;
  forks_detected: number;
  slashing_incidents: number;
  invalid_blocks_rejected: number;
  double_sign_attempts: number;
  malicious_peers_detected: string[];
  incidents: AttackIncident[];
}

export interface AttackScenarioInfo {
  id: string;
  name: string;
  description: string;
  supported_consensus: string[];
  parameters: string[];
  expected_outcome: string;
}

export interface AttackScenarioListResponse {
  scenarios: AttackScenarioInfo[];
  sandbox_status: string;
}

export interface AttackTimelineEvent {
  timestamp: number;
  time_str: string;
  stage: string;
  message: string;
}

export interface AttackExecutionRequest {
  target_node?: string;
  malicious_validator?: string;
  amount?: number;
  custom_params?: Record<string, any>;
}

export interface AttackExecutionResponse {
  attack_id: string;
  attack_type: string;
  status: string;
  target: string;
  is_sandboxed: boolean;
  evidence: Record<string, any>;
  network_response: string;
  timeline: AttackTimelineEvent[];
  final_state: Record<string, any>;
}

export interface WebSocketEvent<T = any> {
  event: string;
  timestamp: number;
  data: T;
}

export type WebSocketStatus = 'connected' | 'reconnecting' | 'disconnected';


// ============================================================================
// Phase 8 Metrics & Telemetry Interfaces
// ============================================================================

export interface MetricPoint {
  timestamp: number;
  value: number;
}

export interface NetworkMetricsResponse {
  active_nodes: number;
  known_peers: number;
  connected_peers: number;
  peer_joins_total: number;
  peer_leaves_total: number;
  history_peer_count: MetricPoint[];
  is_standalone: boolean;
  simulation_mode: string;
}

export interface BlockchainMetricsResponse {
  block_height: number;
  total_blocks_observed: number;
  blocks_created: number;
  blocks_received: number;
  latest_block_timestamp: number | null;
  latest_block_interval_seconds: number | null;
  average_block_interval_seconds: number | null;
  blocks_per_minute: number | null;
  history_block_intervals: MetricPoint[];
  history_blocks_per_minute: MetricPoint[];
  forks_detected_total: number;
  canonical_chain_reorgs_total: number;
}

export interface TransactionMetricsResponse {
  transactions_submitted: number;
  transactions_accepted: number;
  transactions_rejected: number;
  transactions_confirmed: number;
  current_tps: number | null;
  history_tps: MetricPoint[];
  confirmation_latency_avg_seconds: number | null;
}

export interface MempoolMetricsResponse {
  current_mempool_size: number;
  transactions_entered_mempool_total: number;
  transactions_exited_mempool_total: number;
  history_mempool_depth: MetricPoint[];
}

export interface StakeDistributionEntry {
  staker: string;
  name: string;
  stake: number;
  percentage: number;
}

export interface ConsensusMetricsResponse {
  consensus_type: string;
  available: boolean;
  pos?: {
    current_epoch: number | null;
    epoch_seed: string | null;
    validator_count: number;
    active_validator_count: number;
    total_stake: number;
    stake_distribution: StakeDistributionEntry[];
    selected_proposer: string | null;
    slashing_events_total: number;
  } | null;
  pow?: {
    blocks_mined: number;
    difficulty: number | null;
    mining_active: boolean;
  } | null;
  poa?: {
    authority_count: number;
    blocks_produced: number;
  } | null;
}

export interface SecurityMetricsResponse {
  total_attack_attempts: number;
  attacks_by_type: Record<string, number>;
  detected_attacks: number;
  rejected_attacks: number;
  mitigated_attacks: number;
  completed_attacks: number;
  detection_rate_pct: number | null;
  mitigation_rate_pct: number | null;
  canonical_chain_preserved_count: number;
  recent_security_incidents: Array<Record<string, any>>;
}

export interface MetricsSummaryKPIs {
  block_height: number;
  current_tps: number | null;
  mempool_depth: number;
  active_nodes: number;
  peer_count: number;
  consensus_type: string;
  average_block_interval_seconds: number | null;
  total_attacks: number;
  mitigation_rate_pct: number | null;
}

export interface MetricsOverviewResponse {
  status: string;
  telemetry: string;
  timestamp: number;
  is_standalone: boolean;
  simulation_mode: string;
  summary_kpis: MetricsSummaryKPIs;
  network: NetworkMetricsResponse;
  blockchain: BlockchainMetricsResponse;
  transactions: TransactionMetricsResponse;
  mempool: MempoolMetricsResponse;
  consensus: ConsensusMetricsResponse;
  security: SecurityMetricsResponse;
}

export interface MetricsResetResponse {
  status: string;
  message: string;
  timestamp: number;
}
