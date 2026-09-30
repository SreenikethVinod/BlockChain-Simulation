import React from 'react';
import { Blocks, Users, Cpu, Inbox, KeyRound, ShieldAlert } from 'lucide-react';
import {
  NetworkResponse,
  ChainResponse,
  MempoolResponse,
  ConsensusStatusResponse,
  AttackTelemetryResponse,
} from '../types/api';

interface OverviewMetricsProps {
  network: NetworkResponse | null;
  chain: ChainResponse | null;
  mempool: MempoolResponse | null;
  consensus: ConsensusStatusResponse | null;
  attacks: AttackTelemetryResponse | null;
  onNavigateTab: (tab: string) => void;
}

interface TileProps {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  icon: React.ReactNode;
  accent?: string;
  onClick?: () => void;
  testId?: string;
}

const Tile: React.FC<TileProps> = ({ label, value, sub, icon, accent = 'var(--text-muted)', onClick, testId }) => (
  <div
    data-testid={testId}
    onClick={onClick}
    style={{ cursor: onClick ? 'pointer' : 'default' }}
    className="metric-tile metric-tile--clickable"
  >
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
      <span className="label">{label}</span>
      <span style={{ color: accent, opacity: 0.75 }}>{icon}</span>
    </div>
    <div
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '1.125rem',
        fontWeight: 700,
        color: 'var(--text)',
        lineHeight: 1.2,
      }}
    >
      {value}
    </div>
    {sub && (
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.6875rem',
          color: 'var(--text-muted)',
          marginTop: 5,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {sub}
      </div>
    )}
  </div>
);

export const OverviewMetrics: React.FC<OverviewMetricsProps> = ({
  network,
  chain,
  mempool,
  consensus,
  attacks,
  onNavigateTab,
}) => {
  const latestBlock = chain?.chain?.[0] || null;
  const blockHeight = chain ? Math.max(0, chain.length - 1) : 0;
  const nodeCount = network?.node_count ?? 0;
  const mempoolCount = mempool?.count ?? 0;
  const consensusType = (consensus?.consensus_type || network?.consensus_types?.[0] || 'PoS').toUpperCase();
  const totalStake = consensus?.total_stake ?? 0;
  const securityIncidents = (attacks?.slashing_incidents ?? 0) + (attacks?.forks_detected ?? 0);

  const formatHash = (h?: string | null) => {
    if (!h) return '—';
    if (h.length <= 16) return h;
    return `${h.slice(0, 8)}…${h.slice(-6)}`;
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(6, 1fr)',
        gap: 8,
        marginBottom: 20,
      }}
      className="overview-metrics"
    >
      <style>{`
        @media (max-width: 1100px) {
          .overview-metrics { grid-template-columns: repeat(3, 1fr) !important; }
        }
        @media (max-width: 640px) {
          .overview-metrics { grid-template-columns: repeat(2, 1fr) !important; }
        }
      `}</style>

      <Tile
        label="Chain Height"
        value={chain ? `#${blockHeight}` : 'N/A'}
        sub={latestBlock ? formatHash(latestBlock.hash) : 'No blocks'}
        icon={<Blocks size={14} />}
        accent="var(--accent)"
        onClick={() => onNavigateTab('blockchain')}
      />

      <Tile
        label="Active Nodes"
        value={network ? nodeCount : 'N/A'}
        sub={network?.connection_status === 'connected' ? 'P2P mesh synced' : 'Standalone'}
        icon={<Users size={14} />}
        accent="var(--ok)"
        onClick={() => onNavigateTab('nodes')}
      />

      <Tile
        label="Consensus"
        value={consensusType}
        sub={consensusType === 'POS' ? `${consensus?.validator_count ?? 0} validators` : 'Consensus active'}
        icon={<Cpu size={14} />}
        accent="var(--info)"
        onClick={() => onNavigateTab('consensus')}
      />

      <Tile
        label="Mempool"
        value={mempool ? mempoolCount : 'N/A'}
        sub="Pending transactions"
        icon={<Inbox size={14} />}
        accent="var(--warn)"
        onClick={() => onNavigateTab('transactions')}
      />

      <Tile
        label="Pledged Stake"
        value={consensus ? `${totalStake} ⬡` : 'N/A'}
        sub={consensus?.eligibility_status === true ? 'VRF: eligible' : 'VRF: non-validator'}
        icon={<KeyRound size={14} />}
        accent="var(--accent)"
        onClick={() => onNavigateTab('consensus')}
      />

      <Tile
        label="Security"
        value={attacks ? (securityIncidents === 0 ? 'NOMINAL' : `${securityIncidents} ALERTS`) : 'N/A'}
        sub={attacks ? `${attacks.slashing_incidents} slashed · ${attacks.forks_detected} forks` : 'Inactive'}
        icon={<ShieldAlert size={14} />}
        accent={securityIncidents > 0 ? 'var(--fail)' : 'var(--text-dim)'}
        onClick={() => onNavigateTab('security')}
      />
    </div>
  );
};
