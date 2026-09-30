import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { App } from '../App';
import { Header } from '../components/Header';
import { NetworkTopology } from '../components/NetworkTopology';
import { BlockchainExplorer } from '../components/BlockchainExplorer';
import { TransactionPanel } from '../components/TransactionPanel';
import { MempoolViewer } from '../components/MempoolViewer';
import { PoSTelemetryPanel } from '../components/PoSTelemetryPanel';
import { SecurityPanel } from '../components/SecurityPanel';
import { EventConsole } from '../components/EventConsole';
import { AttackLabPanel } from '../components/AttackLabPanel';
import { apiService } from '../services/api';
import { wsService } from '../services/websocket';
import { 
  NetworkResponse, 
  BlockSummary, 
  ConsensusStatusResponse, 
  StakesResponse, 
  AttackTelemetryResponse,
  AttackScenarioInfo,
  AttackExecutionResponse
} from '../types/api';

const mockNetwork: NetworkResponse = {
  room_id: 'TEST-SECTOR-ALPHA',
  node_count: 2,
  nodes: [
    {
      node_id: 'node1',
      name: 'Alpha One',
      host: '127.0.0.1',
      port: 5001,
      consensus: 'pos',
      status: 'active',
      is_self: true,
    },
    {
      node_id: 'node2',
      name: 'Beta Two',
      host: '127.0.0.1',
      port: 5002,
      consensus: 'pos',
      status: 'active',
      is_self: false,
    },
  ],
  consensus_types: ['pos'],
  connection_status: 'connected',
  signalling_url: 'ws://127.0.0.1:8765',
  is_standalone: false,
  simulation_mode: 'live',
};

const mockBlocks: BlockSummary[] = [
  {
    height: 1,
    hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    previous_hash: '0000000000000000000000000000000000000000000000000000000000000000',
    creator: 'Alpha One',
    timestamp: 1790700000,
    transaction_count: 2,
    consensus_type: 'pos',
  },
  {
    height: 0,
    hash: '0000000000000000000000000000000000000000000000000000000000000000',
    previous_hash: null,
    creator: 'Genesis',
    timestamp: 1790690000,
    transaction_count: 1,
    consensus_type: 'pos',
  },
];

const mockConsensus: ConsensusStatusResponse = {
  consensus_type: 'pos',
  epoch_seed: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  validators: [
    { staker: 'Alpha One PEM', staked_amount: 100, is_local: true },
    { staker: 'Beta Two PEM', staked_amount: 50, is_local: false },
  ],
  validator_count: 2,
  total_stake: 150,
  eligibility_status: true,
  latest_block: mockBlocks[0],
  chain_length: 2,
  chain_weight: 150,
  slashing_events: [],
};

const mockStakes: StakesResponse = {
  total_staked: 150,
  staker_count: 2,
  current_epoch_stakes: [
    { id: 's1', staker: 'Alpha One', amt: 100, timestamp: 1790700000 },
    { id: 's2', staker: 'Beta Two', amt: 50, timestamp: 1790700000 },
  ],
  node_is_staker: true,
  node_staked_amt: 100,
  epoch_remaining_seconds: 42.5,
};

const mockAttacks: AttackTelemetryResponse = {
  status: 'monitoring',
  forks_detected: 1,
  slashing_incidents: 2,
  invalid_blocks_rejected: 0,
  double_sign_attempts: 1,
  malicious_peers_detected: [],
  incidents: [
    { type: 'validator_slashed', time: 1790700000, validator: 'Rogue Node', reason: 'Double signing' },
  ],
};

const mockScenarios: AttackScenarioInfo[] = [
  {
    id: 'double_sign',
    name: 'Double Signing',
    description: 'Validator signs conflicting blocks at same height.',
    supported_consensus: ['pos'],
    parameters: ['malicious_validator'],
    expected_outcome: 'Validator slashed, canonical chain preserved.'
  },
  {
    id: 'double_spend',
    name: 'Double Spend Attempt',
    description: 'Conflicting transactions attempting to spend same balance.',
    supported_consensus: ['pos', 'pow', 'poa'],
    parameters: ['amount'],
    expected_outcome: 'Conflicting spend rejected.'
  },
  {
    id: 'fork',
    name: 'Competing Fork Attack',
    description: 'Adversarial branch diverging from canonical ledger.',
    supported_consensus: ['pos'],
    parameters: ['target_node'],
    expected_outcome: 'Heaviest chain rule retains canonical branch.'
  },
  {
    id: 'invalid_vrf',
    name: 'Invalid VRF Proof',
    description: 'Fraudulent lottery output rejection.',
    supported_consensus: ['pos'],
    parameters: ['target_node'],
    expected_outcome: 'Block discarded.'
  },
  {
    id: 'invalid_signature',
    name: 'Invalid Block Signature',
    description: 'Corrupted signature bytes failure.',
    supported_consensus: ['pos', 'pow', 'poa'],
    parameters: ['target_node'],
    expected_outcome: 'BadSignatureError caught.'
  },
  {
    id: 'fake_stake',
    name: 'Fake / Unauthorized Stake',
    description: 'Stake claiming unauthorized balance.',
    supported_consensus: ['pos'],
    parameters: ['amount'],
    expected_outcome: 'Stake rejected.'
  },
];

const mockExecutionResponse: AttackExecutionResponse = {
  attack_id: 'atk_test_1234',
  attack_type: 'double_sign',
  status: 'mitigated',
  target: 'node1',
  is_sandboxed: true,
  evidence: {
    block_a_hash: 'hash_a_1111',
    block_b_hash: 'hash_b_2222',
    validator: 'rogue_validator_pk',
    slashing_reason: 'Double signing detected at height 1'
  },
  network_response: 'Validator slashed for double signing; canonical chain retained',
  timeline: [
    { timestamp: 1790700000, time_str: '00:00:01', stage: 'READY', message: 'Attack Lab sandbox initialized' },
    { timestamp: 1790700001, time_str: '00:00:02', stage: 'ARMED', message: 'Adversary harness armed' },
    { timestamp: 1790700002, time_str: '00:00:03', stage: 'EXECUTING', message: 'Rogue validator generated conflicting blocks' },
    { timestamp: 1790700003, time_str: '00:00:04', stage: 'DETECTED', message: 'Equivocation evidence verified' },
    { timestamp: 1790700004, time_str: '00:00:05', stage: 'MITIGATED', message: 'Validator slashed. Stake revoked.' },
    { timestamp: 1790700005, time_str: '00:00:06', stage: 'COMPLETE', message: 'Canonical chain preserved.' },
  ],
  final_state: {
    canonical_height: 2,
    validator_slashed: true
  }
};

describe('Mission Control Dashboard Unit & Integration Suite', () => {
  beforeEach(() => {
    vi.spyOn(apiService, 'getNetwork').mockResolvedValue(mockNetwork);
    vi.spyOn(apiService, 'getNodes').mockResolvedValue({
      total: 2,
      nodes: [
        {
          node_id: 'node1',
          name: 'Alpha One',
          public_key: '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...\n-----END PUBLIC KEY-----',
          consensus: 'pos',
          host: '127.0.0.1',
          port: 5001,
          status: 'active',
          balance: 100,
          is_self: true,
        },
      ],
    });
    vi.spyOn(apiService, 'getChain').mockResolvedValue({
      length: 2,
      chain: mockBlocks,
    });
    vi.spyOn(apiService, 'getMempool').mockResolvedValue({
      count: 1,
      transactions: [
        { id: 'tx-001', sender: 'Alpha', receiver: 'Beta', payload: 10, timestamp: 1790701000 },
      ],
    });
    vi.spyOn(apiService, 'getConsensusStatus').mockResolvedValue(mockConsensus);
    vi.spyOn(apiService, 'getStakes').mockResolvedValue(mockStakes);
    vi.spyOn(apiService, 'getAttackTelemetry').mockResolvedValue(mockAttacks);
    vi.spyOn(apiService, 'getAttackScenarios').mockResolvedValue({
      scenarios: mockScenarios,
      sandbox_status: 'LOCAL_SANDBOX_ENFORCED',
    });
    vi.spyOn(apiService, 'executeAttack').mockResolvedValue(mockExecutionResponse);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // 1. Dashboard loads
  it('1. loads dashboard successfully with title and telemetry hook', async () => {
    render(<App />);
    expect(screen.getByText(/BLOCKCHAIN MISSION CONTROL/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Mission Control Status: Stellar/i).length).toBeGreaterThan(0);
  });

  // 2. API connection succeeds
  it('2. API connection succeeds and renders network metrics', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getAllByText('TEST-SECTOR-ALPHA').length).toBeGreaterThan(0);
      expect(screen.getByTestId('mode-live')).toBeInTheDocument();
    });
  });

  // 3. API unavailable state
  it('3. handles API unavailable state gracefully with offline banner', async () => {
    vi.spyOn(apiService, 'getNetwork').mockRejectedValue(new Error('Network error'));
    render(<App />);
    await waitFor(() => {
      
      expect(screen.getByText(/Backend Offline/i)).toBeInTheDocument();
    });
  });

  // 4. Node list rendering
  it('4. renders constellation nodes properly in table', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getAllByText('TEST-SECTOR-ALPHA').length).toBeGreaterThan(0);
    });
    // Switch to nodes tab
    const nodesTab = screen.getByRole('button', { name: /Nodes/i });
    fireEvent.click(nodesTab);

    await waitFor(() => {
      expect(screen.getAllByText('Alpha One').length).toBeGreaterThan(0);
      expect(screen.getAllByText('node1').length).toBeGreaterThan(0);
      expect(screen.getByText('127.0.0.1:5001')).toBeInTheDocument();
    });
  });

  // 5. Network topology rendering
  it('5. renders network topology SVG with vessels and separate discovery station', () => {
    const onSelectNode = vi.fn();
    render(<NetworkTopology network={mockNetwork} onSelectNode={onSelectNode} />);
    expect(screen.getByText(/P2P Mesh Topology/i)).toBeInTheDocument();
    expect(screen.getByText('Signalling (discovery only)')).toBeInTheDocument();
    expect(screen.getByText('Alpha One')).toBeInTheDocument();
    expect(screen.getByText('Beta Two')).toBeInTheDocument();
  });

  // 6. Block rendering
  it('6. renders blockchain explorer blocks with height and hash', () => {
    const onPageChange = vi.fn();
    render(
      <BlockchainExplorer
        blocks={mockBlocks}
        totalBlocks={2}
        currentPage={0}
        pageSize={10}
        onPageChange={onPageChange}
      />
    );
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#0')).toBeInTheDocument();
    expect(screen.getByText(/Alpha One/i)).toBeInTheDocument();
  });

  // 7. Transaction submission
  it('7. submits transaction through POST /api/transactions with valid inputs', async () => {
    const mockSubmit = vi.spyOn(apiService, 'submitTransaction').mockResolvedValue({
      status: 'submitted',
      tx_id: 'tx-new-999',
      sender: 'Alpha One',
      receiver: 'Beta Two',
      amount: 5.0,
      timestamp: 1790702000,
    });

    render(<TransactionPanel availableBalance={100} />);
    
    const receiverInput = screen.getByTestId('input-receiver');
    const amountInput = screen.getByTestId('input-amount');
    const submitBtn = screen.getByTestId('submit-tx-btn');

    await userEvent.type(receiverInput, 'Beta Two');
    await userEvent.type(amountInput, '5.0');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith({ receiver: 'Beta Two', amount: 5.0 });
      expect(screen.getByTestId('tx-success-message')).toBeInTheDocument();
    });
  });

  // 8. Validation error handling
  it('8. handles validation error on negative or zero transaction amount', async () => {
    render(<TransactionPanel availableBalance={100} />);
    const receiverInput = screen.getByTestId('input-receiver');
    const amountInput = screen.getByTestId('input-amount');
    const submitBtn = screen.getByTestId('submit-tx-btn');

    await userEvent.type(receiverInput, 'Beta Two');
    await userEvent.type(amountInput, '-5');
    fireEvent.click(submitBtn);

    expect(screen.getByTestId('tx-error-message')).toBeInTheDocument();
    expect(screen.getByText(/Amount must be a positive number/i)).toBeInTheDocument();
  });

  // 9. WebSocket connection
  it('9. WebSocket status indicates live connection when active', () => {
    render(
      <Header
        network={mockNetwork}
        wsStatus="connected"
        isBackendOnline={true}
        onRefresh={() => {}}
        isRefreshing={false}
      />
    );
    expect(screen.getByText('WS LIVE')).toBeInTheDocument();
  });

  // 10. WebSocket reconnection
  it('10. WebSocket status indicates reconnecting when connection drops', () => {
    render(
      <Header
        network={mockNetwork}
        wsStatus="reconnecting"
        isBackendOnline={true}
        onRefresh={() => {}}
        isRefreshing={false}
      />
    );
    expect(screen.getByText('WS RECONNECT')).toBeInTheDocument();
  });

  // 11. Event rendering
  it('11. renders real-time WebSocket events in event console', () => {
    const testEvents = [
      { event: 'block_created', timestamp: 1790700000, data: { height: 1 } },
      { event: 'transaction_received', timestamp: 1790700001, data: { id: 'tx-1' } },
      { event: 'validator_slashed', timestamp: 1790700002, data: { validator: 'bad' } },
    ];
    render(<EventConsole events={testEvents} onClear={() => {}} />);
    expect(screen.getByText('BLOCK')).toBeInTheDocument();
    expect(screen.getByText('TX')).toBeInTheDocument();
    expect(screen.getByText('SLASHED')).toBeInTheDocument();
  });

  // 12. No private-key fields rendered
  it('12. security verification: never renders private keys or secret fields', () => {
    const { container } = render(<App />);
    const html = container.innerHTML;
    expect(html).not.toContain('PRIVATE KEY');
    expect(html).not.toContain('private_key');
    expect(html).not.toContain('private_key_pem');
  });

  // 13. Empty-state handling
  it('13. handles empty mempool and topology empty state intentionally', () => {
    render(<MempoolViewer mempool={{ count: 0, transactions: [] }} />);
    expect(screen.getByTestId('mempool-empty-state')).toBeInTheDocument();
    expect(screen.getByText(/Queue empty/i)).toBeInTheDocument();
  });

  // 14. PoS telemetry rendering
  it('14. renders PoS telemetry, validator roster, and epoch seed', () => {
    render(<PoSTelemetryPanel consensus={mockConsensus} stakes={mockStakes} />);
    expect(screen.getByText(/Proof-of-Stake Consensus & VRF Telemetry/i)).toBeInTheDocument();
    expect(screen.getByText(/ELIGIBLE FOR NEXT BLOCK/i)).toBeInTheDocument();
    expect(screen.getByText('150 ⬡')).toBeInTheDocument();
  });

  // 15. Security telemetry rendering
  it('15. renders read-only security telemetry and slashing incidents', () => {
    render(<SecurityPanel attacks={mockAttacks} />);
    expect(screen.getByText(/Security Telemetry/i)).toBeInTheDocument();
    expect(screen.getByText('Forks detected')).toBeInTheDocument();
  });

  // 16. Attack Lab tab rendering
  it('16. renders Attack Lab tab with local sandbox banner and all 6 attack vector cards', async () => {
    render(<App />);
    
    // Wait for initial dashboard hydration
    await waitFor(() => {
      expect(screen.getAllByText('TEST-SECTOR-ALPHA').length).toBeGreaterThan(0);
    });

    const attackLabTab = screen.getByTestId('tab-attack_lab');
    expect(attackLabTab).toBeInTheDocument();
    await userEvent.click(attackLabTab);

    await waitFor(() => {
      expect(screen.getByText(/LOCAL SANDBOX ENFORCED/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Double Signing/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Double Spend Attempt/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Competing Fork Attack/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Invalid VRF Proof/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Invalid Block Signature/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Fake \/ Unauthorized Stake/i).length).toBeGreaterThan(0);
    });
  });

  // 17. Execute Double Sign Attack
  it('17. executes double-sign attack scenario and renders timeline stages and forensic evidence', async () => {
    render(<AttackLabPanel scenarios={mockScenarios} latestAttackEvent={null} />);
    
    const launchBtn = screen.getByRole('button', { name: /Execute Attack Scenario/i });
    expect(launchBtn).toBeInTheDocument();
    fireEvent.click(launchBtn);

    await waitFor(() => {
      expect(screen.getByText(/Validator slashed for double signing/i)).toBeInTheDocument();
      expect(screen.getByText(/hash_a_1111/i)).toBeInTheDocument();
      expect(screen.getByText(/hash_b_2222/i)).toBeInTheDocument();
      expect(screen.getByText(/Verdict: mitigated/i)).toBeInTheDocument();
    });
  });

  // 18. Execute Double Spend with parameter input
  it('18. renders attack parameters and executes double-spend with spend amount input', async () => {
    render(<AttackLabPanel scenarios={mockScenarios} latestAttackEvent={null} />);
    
    const doubleSpendCard = screen.getByText(/Double Spend Attempt/i);
    fireEvent.click(doubleSpendCard);

    expect(screen.getByText(/Spend Amount \(Each Transaction\)/i)).toBeInTheDocument();
    const amountInput = screen.getByRole('spinbutton');
    fireEvent.change(amountInput, { target: { value: '45' } });

    const launchBtn = screen.getByRole('button', { name: /Execute Attack Scenario/i });
    fireEvent.click(launchBtn);

    await waitFor(() => {
      expect(apiService.executeAttack).toHaveBeenCalledWith('double_spend', expect.objectContaining({ amount: 45 }));
    });
  });

  // 19. Security verification: no private keys in Attack Lab
  it('19. security verification: AttackLabPanel never displays or requests private keys', () => {
    const { container } = render(<AttackLabPanel scenarios={mockScenarios} latestAttackEvent={null} />);
    const html = container.innerHTML;
    expect(html).not.toContain('PRIVATE KEY');
    expect(html).not.toContain('private_key');
    expect(html).not.toContain('private_key_pem');
    expect(html).not.toContain('BEGIN EC PRIVATE');
  });
});
