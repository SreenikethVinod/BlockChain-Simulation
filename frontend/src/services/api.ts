/**
 * Deep-Space Mission Control — REST API Client
 * Clean HTTP client for FastAPI backend with robust error parsing.
 */

import {
  NetworkResponse,
  NodeListResponse,
  NodeDetailResponse,
  ChainResponse,
  BlockDetail,
  TransactionListResponse,
  TransactionCreateRequest,
  TransactionResponse,
  MempoolResponse,
  StakesResponse,
  ConsensusStatusResponse,
  AttackTelemetryResponse,
  AttackScenarioListResponse,
  AttackExecutionRequest,
  AttackExecutionResponse,
  MetricsOverviewResponse,
  NetworkMetricsResponse,
  BlockchainMetricsResponse,
  TransactionMetricsResponse,
  MempoolMetricsResponse,
  ConsensusMetricsResponse,
  SecurityMetricsResponse,
  MetricsResetResponse,
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_URL || '';

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
    });

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const body = await res.json();
        if (body.detail) {
          if (Array.isArray(body.detail)) {
            errorDetail = body.detail.map((d: any) => `${d.loc?.join('.')}: ${d.msg}`).join(', ');
          } else {
            errorDetail = String(body.detail);
          }
        }
      } catch {
        // Fallback to status text
      }
      throw new Error(errorDetail);
    }

    return await res.json();
  } catch (err: any) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(`Mission Control station unreachable at ${API_BASE || 'localhost'}. Ensure backend is running.`);
    }
    throw err;
  }
}

export const apiService = {
  getStatus: () => fetchJson<any>('/api/status'),

  getNetwork: () => fetchJson<NetworkResponse>('/api/network'),

  getNodes: () => fetchJson<NodeListResponse>('/api/nodes'),

  getNode: (nodeId: string) => fetchJson<NodeDetailResponse>(`/api/nodes/${encodeURIComponent(nodeId)}`),

  getChain: (limit = 50, offset = 0, reverse = true) =>
    fetchJson<ChainResponse>(`/api/chain?limit=${limit}&offset=${offset}&reverse=${reverse}`),

  getBlock: (height: number) => fetchJson<BlockDetail>(`/api/chain/${height}`),

  getTransactions: (limit = 100, offset = 0) =>
    fetchJson<TransactionListResponse>(`/api/transactions?limit=${limit}&offset=${offset}`),

  submitTransaction: (data: TransactionCreateRequest) =>
    fetchJson<TransactionResponse>('/api/transactions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getMempool: () => fetchJson<MempoolResponse>('/api/mempool'),

  getStakes: () => fetchJson<StakesResponse>('/api/stakes'),

  getConsensusStatus: () => fetchJson<ConsensusStatusResponse>('/api/consensus/status'),

  getAttackTelemetry: () => fetchJson<AttackTelemetryResponse>('/api/attacks/telemetry'),

  getAttackScenarios: () => fetchJson<AttackScenarioListResponse>('/api/attacks/scenarios'),

  executeAttack: (attackType: string, data?: AttackExecutionRequest) =>
    fetchJson<AttackExecutionResponse>(`/api/attacks/${encodeURIComponent(attackType)}`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    }),

  getAttackHistory: (attackId: string) =>
    fetchJson<AttackExecutionResponse>(`/api/attacks/history/${encodeURIComponent(attackId)}`),

  // Phase 8 Metrics & Telemetry
  getMetrics: () => fetchJson<MetricsOverviewResponse>('/api/metrics'),

  getNetworkMetrics: () => fetchJson<NetworkMetricsResponse>('/api/metrics/network'),

  getBlockchainMetrics: () => fetchJson<BlockchainMetricsResponse>('/api/metrics/blockchain'),

  getTransactionMetrics: () => fetchJson<TransactionMetricsResponse>('/api/metrics/transactions'),

  getMempoolMetrics: () => fetchJson<MempoolMetricsResponse>('/api/metrics/mempool'),

  getConsensusMetrics: () => fetchJson<ConsensusMetricsResponse>('/api/metrics/consensus'),

  getSecurityMetrics: () => fetchJson<SecurityMetricsResponse>('/api/metrics/security'),

  resetMetrics: () =>
    fetchJson<MetricsResetResponse>('/api/metrics/reset', {
      method: 'POST',
    }),
};

export const api = apiService;
