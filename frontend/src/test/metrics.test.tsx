import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { MetricsAnalyticsPanel } from '../components/MetricsAnalyticsPanel';
import { MetricsOverviewResponse } from '../types/api';

const mockMetrics: MetricsOverviewResponse = {
  status: 'online',
  telemetry: 'Mission Control Status: Stellar',
  timestamp: 1700000000,
  is_standalone: true,
  simulation_mode: 'standalone',
  summary_kpis: {
    block_height: 42,
    current_tps: 3.5,
    mempool_depth: 7,
    active_nodes: 3,
    peer_count: 2,
    consensus_type: 'pos',
    average_block_interval_seconds: 12.4,
    total_attacks: 4,
    mitigation_rate_pct: 100.0,
  },
  network: {
    active_nodes: 3,
    known_peers: 2,
    connected_peers: 2,
    peer_joins_total: 5,
    peer_leaves_total: 2,
    history_peer_count: [
      { timestamp: 1700000000, value: 2 },
      { timestamp: 1700000010, value: 2 },
    ],
    is_standalone: true,
    simulation_mode: 'standalone',
  },
  blockchain: {
    block_height: 42,
    total_blocks_observed: 42,
    blocks_created: 30,
    blocks_received: 12,
    latest_block_timestamp: 1700000000,
    latest_block_interval_seconds: 11.2,
    average_block_interval_seconds: 12.4,
    blocks_per_minute: 5.0,
    history_block_intervals: [
      { timestamp: 1700000000, value: 12.0 },
      { timestamp: 1700000012, value: 12.8 },
    ],
    history_blocks_per_minute: [
      { timestamp: 1700000000, value: 5.0 },
    ],
    forks_detected_total: 1,
    canonical_chain_reorgs_total: 1,
  },
  transactions: {
    transactions_submitted: 150,
    transactions_accepted: 148,
    transactions_rejected: 2,
    transactions_confirmed: 140,
    current_tps: 3.5,
    history_tps: [
      { timestamp: 1700000000, value: 2.5 },
      { timestamp: 1700000010, value: 3.5 },
    ],
    confirmation_latency_avg_seconds: 4.2,
  },
  mempool: {
    current_mempool_size: 7,
    transactions_entered_mempool_total: 150,
    transactions_exited_mempool_total: 143,
    history_mempool_depth: [
      { timestamp: 1700000000, value: 5 },
      { timestamp: 1700000010, value: 7 },
    ],
  },
  consensus: {
    consensus_type: 'pos',
    available: true,
    pos: {
      current_epoch: 4,
      epoch_seed: 'seed_abcdef123456',
      validator_count: 2,
      active_validator_count: 2,
      total_stake: 1000,
      stake_distribution: [
        { staker: 'val_alpha', name: 'Alpha', stake: 600, percentage: 60.0 },
        { staker: 'val_beta', name: 'Beta', stake: 400, percentage: 40.0 },
      ],
      selected_proposer: 'val_alpha',
      slashing_events_total: 0,
    },
    pow: null,
    poa: null,
  },
  security: {
    total_attack_attempts: 4,
    attacks_by_type: {
      double_sign: 2,
      double_spend: 1,
      fork: 1,
      invalid_vrf: 0,
      invalid_signature: 0,
      fake_stake: 0,
    },
    detected_attacks: 4,
    rejected_attacks: 2,
    mitigated_attacks: 2,
    completed_attacks: 4,
    detection_rate_pct: 100.0,
    mitigation_rate_pct: 100.0,
    canonical_chain_preserved_count: 4,
    recent_security_incidents: [
      { attack_type: 'double_sign', stage: 'MITIGATED', timestamp: 1700000000, details: {} },
    ],
  },
};

describe('Phase 8 Metrics & Telemetry Suite', () => {
  const onRefresh = vi.fn();
  const onReset = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. renders panel title and mode badge correctly', () => {
    render(
      <MetricsAnalyticsPanel
        metrics={mockMetrics}
        onRefresh={onRefresh}
        onReset={onReset}
      />
    );

    expect(screen.getByText(/REAL-TIME TELEMETRY & ANALYTICS/i)).toBeInTheDocument();
    expect(screen.getByText(/STANDALONE OBSERVATION MODE/i)).toBeInTheDocument();
  });

  it('2. displays authentic KPI values without placeholder fabrication', () => {
    render(
      <MetricsAnalyticsPanel
        metrics={mockMetrics}
        onRefresh={onRefresh}
        onReset={onReset}
      />
    );

    // Block height
    expect(screen.getByText('42')).toBeInTheDocument();
    // TPS
    expect(screen.getByText('3.50')).toBeInTheDocument();
    // Mempool depth
    expect(screen.getByText('7')).toBeInTheDocument();
    // Avg interval
    expect(screen.getByText('12.4s')).toBeInTheDocument();
    // Mitigation rate
    expect(screen.getAllByText('100.0%').length).toBeGreaterThanOrEqual(1);
  });

  it('3. renders LIVE SIMULATION badge when in live mode', () => {
    const liveMetrics = {
      ...mockMetrics,
      is_standalone: false,
      simulation_mode: 'live',
    };

    render(
      <MetricsAnalyticsPanel
        metrics={liveMetrics}
        onRefresh={onRefresh}
        onReset={onReset}
      />
    );

    expect(screen.getByText(/LIVE SIMULATION TELEMETRY/i)).toBeInTheDocument();
  });

  it('4. displays proper empty state when telemetry history is empty', () => {
    const emptyMetrics: MetricsOverviewResponse = {
      ...mockMetrics,
      blockchain: {
        ...mockMetrics.blockchain,
        history_block_intervals: [],
        average_block_interval_seconds: null,
      },
      transactions: {
        ...mockMetrics.transactions,
        history_tps: [],
        current_tps: 0.0,
      },
      security: {
        ...mockMetrics.security,
        total_attack_attempts: 0,
        recent_security_incidents: [],
      },
    };

    render(
      <MetricsAnalyticsPanel
        metrics={emptyMetrics}
        onRefresh={onRefresh}
        onReset={onReset}
      />
    );

    // Empty TPS state
    expect(screen.getByText(/Insufficient telemetry data/i)).toBeInTheDocument();
    // Empty block intervals state
    expect(screen.getByText(/Insufficient block intervals/i)).toBeInTheDocument();
    // Empty security state
    expect(screen.getByText(/No adversarial attacks executed in current session/i)).toBeInTheDocument();
  });

  it('5. handles null metrics object gracefully without throwing', () => {
    render(
      <MetricsAnalyticsPanel
        metrics={null}
        onRefresh={onRefresh}
        onReset={onReset}
      />
    );

    expect(screen.getByText(/REAL-TIME TELEMETRY & ANALYTICS/i)).toBeInTheDocument();
  });

  it('6. invokes onRefresh when refresh button is clicked', () => {
    render(
      <MetricsAnalyticsPanel
        metrics={mockMetrics}
        onRefresh={onRefresh}
        onReset={onReset}
      />
    );

    const refreshBtn = screen.getByRole('button', { name: /refresh/i });
    fireEvent.click(refreshBtn);
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it('7. triggers onReset when reset telemetry is confirmed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(
      <MetricsAnalyticsPanel
        metrics={mockMetrics}
        onRefresh={onRefresh}
        onReset={onReset}
      />
    );

    const resetBtn = screen.getByRole('button', { name: /reset telemetry/i });
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(onReset).toHaveBeenCalledTimes(1);
    });
  });

  it('8. handles PoW consensus gracefully without rendering invalid staking charts', () => {
    const powMetrics: MetricsOverviewResponse = {
      ...mockMetrics,
      consensus: {
        consensus_type: 'pow',
        available: true,
        pos: null,
        pow: {
          blocks_mined: 10,
          difficulty: 4,
          mining_active: true,
        },
        poa: null,
      },
    };

    render(
      <MetricsAnalyticsPanel
        metrics={powMetrics}
        onRefresh={onRefresh}
        onReset={onReset}
      />
    );

    expect(screen.getByText(/Consensus is POW — Staking metrics not applicable/i)).toBeInTheDocument();
  });
});
