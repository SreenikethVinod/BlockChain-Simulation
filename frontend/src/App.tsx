import React, { useEffect, useState, useCallback } from 'react';
import {
  Activity,
  Radio,
  Layers,
  Send,
  Cpu,
  ShieldAlert,
  Terminal,
  Users,
  Blocks,
  WifiOff,
  Flame,
} from 'lucide-react';

import {
  NetworkResponse,
  NodeDetailResponse,
  ChainResponse,
  MempoolResponse,
  ConsensusStatusResponse,
  StakesResponse,
  AttackTelemetryResponse,
  AttackScenarioInfo,
  MetricsOverviewResponse,
  WebSocketEvent,
  WebSocketStatus,
} from './types/api';
import { apiService } from './services/api';
import { wsService } from './services/websocket';

import { Header } from './components/Header';
import { OverviewMetrics } from './components/OverviewMetrics';
import { NetworkTopology } from './components/NetworkTopology';
import { NodeInspectorModal } from './components/NodeInspectorModal';
import { BlockchainExplorer } from './components/BlockchainExplorer';
import { TransactionPanel } from './components/TransactionPanel';
import { MempoolViewer } from './components/MempoolViewer';
import { PoSTelemetryPanel } from './components/PoSTelemetryPanel';
import { EventConsole } from './components/EventConsole';
import { SecurityPanel } from './components/SecurityPanel';
import { AttackLabPanel } from './components/AttackLabPanel';
import { MetricsAnalyticsPanel } from './components/MetricsAnalyticsPanel';

const TABS = [
  { id: 'overview',     label: 'Overview',          icon: <Radio size={13} /> },
  { id: 'nodes',        label: 'Nodes',              icon: <Users size={13} /> },
  { id: 'blockchain',   label: 'Ledger',             icon: <Blocks size={13} /> },
  { id: 'transactions', label: 'Transactions',       icon: <Send size={13} /> },
  { id: 'consensus',    label: 'PoS Telemetry',      icon: <Cpu size={13} /> },
  { id: 'security',     label: 'Security',           icon: <ShieldAlert size={13} /> },
  { id: 'attack_lab',   label: 'Attack Lab',         icon: <Flame size={13} style={{ color: 'var(--fail)' }} /> },
  { id: 'analytics',    label: 'Metrics',            icon: <Activity size={13} /> },
];

export function App() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [network, setNetwork] = useState<NetworkResponse | null>(null);
  const [nodes, setNodes] = useState<NodeDetailResponse[]>([]);
  const [chain, setChain] = useState<ChainResponse | null>(null);
  const [mempool, setMempool] = useState<MempoolResponse | null>(null);
  const [consensus, setConsensus] = useState<ConsensusStatusResponse | null>(null);
  const [stakes, setStakes] = useState<StakesResponse | null>(null);
  const [attacks, setAttacks] = useState<AttackTelemetryResponse | null>(null);
  const [attackScenarios, setAttackScenarios] = useState<AttackScenarioInfo[]>([]);
  const [metrics, setMetrics] = useState<MetricsOverviewResponse | null>(null);
  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const [wsStatus, setWsStatus] = useState<WebSocketStatus>('disconnected');
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const [chainPage, setChainPage] = useState<number>(0);
  const chainPageSize = 10;

  const loadDashboardData = useCallback(async () => {
    try {
      const [netRes, nodesRes, chainRes, mempoolRes, consensusRes, stakesRes, attacksRes, scenariosRes, metricsRes] =
        await Promise.allSettled([
          apiService.getNetwork(),
          apiService.getNodes(),
          apiService.getChain(chainPageSize, chainPage * chainPageSize, true),
          apiService.getMempool(),
          apiService.getConsensusStatus(),
          apiService.getStakes(),
          apiService.getAttackTelemetry(),
          apiService.getAttackScenarios(),
          apiService.getMetrics(),
        ]);

      if (netRes.status === 'fulfilled') {
        setNetwork(netRes.value);
        setIsBackendOnline(true);
      } else {
        setIsBackendOnline(false);
      }

      if (nodesRes.status === 'fulfilled') setNodes(nodesRes.value.nodes);
      if (chainRes.status === 'fulfilled') setChain(chainRes.value);
      if (mempoolRes.status === 'fulfilled') setMempool(mempoolRes.value);
      if (consensusRes.status === 'fulfilled') setConsensus(consensusRes.value);
      if (stakesRes.status === 'fulfilled') setStakes(stakesRes.value);
      if (attacksRes.status === 'fulfilled') setAttacks(attacksRes.value);
      if (scenariosRes.status === 'fulfilled') setAttackScenarios(scenariosRes.value.scenarios);
      if (metricsRes && metricsRes.status === 'fulfilled') setMetrics(metricsRes.value);
    } catch {
      setIsBackendOnline(false);
    }
  }, [chainPage, chainPageSize]);

  useEffect(() => {
    loadDashboardData();

    const unsubStatus = wsService.onStatus((status) => {
      setWsStatus(status);
    });

    const unsubEvents = wsService.subscribe((evt: WebSocketEvent) => {
      setEvents((prev) => [evt, ...prev.slice(0, 99)]);

      if (evt.event === 'metrics_updated') {
        apiService.getMetrics().then(setMetrics).catch(() => {});
      } else if (evt.event === 'transaction_received') {
        apiService.getMetrics().then(setMetrics).catch(() => {});
        apiService.getMempool().then(setMempool).catch(() => {});
      } else if (evt.event === 'block_created' || evt.event === 'block_received') {
        apiService.getChain(chainPageSize, chainPage * chainPageSize, true).then(setChain).catch(() => {});
        apiService.getMempool().then(setMempool).catch(() => {});
        apiService.getConsensusStatus().then(setConsensus).catch(() => {});
      } else if (evt.event === 'peer_joined' || evt.event === 'peer_left') {
        apiService.getNetwork().then(setNetwork).catch(() => {});
        apiService.getNodes().then((r) => setNodes(r.nodes)).catch(() => {});
      } else if (
        evt.event === 'fork_detected' ||
        evt.event === 'validator_slashed' ||
        evt.event.startsWith('attack_')
      ) {
        apiService.getAttackTelemetry().then(setAttacks).catch(() => {});
        apiService.getConsensusStatus().then(setConsensus).catch(() => {});
      }
    });

    const interval = setInterval(() => {
      loadDashboardData();
    }, 4000);

    return () => {
      clearInterval(interval);
      unsubStatus();
      unsubEvents();
    };
  }, [loadDashboardData, chainPage, chainPageSize]);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await loadDashboardData();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const localNode = nodes.find((n) => n.is_self);
  const availableBalance = localNode?.balance ?? null;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Header
        network={network}
        wsStatus={wsStatus}
        isBackendOnline={isBackendOnline}
        onRefresh={handleManualRefresh}
        isRefreshing={isRefreshing}
        telemetryPhrase="Mission Control Status: Stellar"
      />

      <main style={{ flex: 1, maxWidth: 1440, width: '100%', margin: '0 auto', padding: '20px 20px 40px' }}>

        {/* Offline Banner */}
        {!isBackendOnline && (
          <div
            data-testid="backend-offline-banner"
            className="alert alert--error animate-fade-in"
            style={{ marginBottom: 16, alignItems: 'center', justifyContent: 'space-between' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <WifiOff size={15} style={{ flexShrink: 0 }} />
              <div>
                <strong style={{ display: 'block', marginBottom: 2 }}>Backend Offline</strong>
                <span style={{ color: 'inherit', opacity: 0.8 }}>
                  Cannot reach 127.0.0.1:8000 — run <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>python start_backend.py</code>
                </span>
              </div>
            </div>
            <button onClick={handleManualRefresh} className="btn btn--ghost" style={{ flexShrink: 0 }}>
              Retry
            </button>
          </div>
        )}

        {/* Overview Metrics Strip */}
        <OverviewMetrics
          network={network}
          chain={chain}
          mempool={mempool}
          consensus={consensus}
          attacks={attacks}
          onNavigateTab={setActiveTab}
        />

        {/* Tab Navigation */}
        <nav className="tab-nav" style={{ marginBottom: 20 }}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              data-testid={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-btn ${activeTab === tab.id ? 'tab-btn--active' : ''}`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <NetworkTopology
              network={network}
              onSelectNode={setSelectedNodeId}
              selectedNodeId={selectedNodeId}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }} className="tx-grid">
              <style>{`@media (max-width: 768px) { .tx-grid { grid-template-columns: 1fr !important; } }`}</style>
              <TransactionPanel
                availableBalance={availableBalance}
                onTransactionSubmitted={() => {
                  apiService.getMempool().then(setMempool).catch(() => {});
                }}
              />
              <MempoolViewer mempool={mempool} />
            </div>
            <EventConsole events={events} onClear={() => setEvents([])} />
          </div>
        )}

        {/* Tab 2: Nodes */}
        {activeTab === 'nodes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <NetworkTopology
              network={network}
              onSelectNode={setSelectedNodeId}
              selectedNodeId={selectedNodeId}
            />
            <div className="panel" style={{ padding: '16px 20px' }}>
              <div className="section-header">
                <h3 className="section-title">
                  <Users size={14} style={{ color: 'var(--ok)' }} />
                  Active Nodes ({nodes.length})
                </h3>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                  Click a row to inspect
                </span>
              </div>
              {nodes.length === 0 ? (
                <div data-testid="no-active-nodes-state" style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                  No active nodes detected.
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Node ID</th>
                        <th>Endpoint</th>
                        <th>Consensus</th>
                        <th>Status</th>
                        <th style={{ textAlign: 'right' }}>Balance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {nodes.map((n) => (
                        <tr
                          key={n.node_id}
                          onClick={() => setSelectedNodeId(n.node_id)}
                          style={{ cursor: 'pointer' }}
                        >
                          <td style={{ color: 'var(--text)', fontWeight: 600 }}>
                            {n.name}
                            {n.is_self && (
                              <span style={{ marginLeft: 6, fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--accent)', border: '1px solid var(--accent-dim)', padding: '1px 5px', borderRadius: 'var(--radius-sm)' }}>
                                LOCAL
                              </span>
                            )}
                          </td>
                          <td style={{ color: 'var(--text-muted)' }}>{n.node_id}</td>
                          <td style={{ color: 'var(--text-muted)' }}>{n.host}:{n.port}</td>
                          <td style={{ color: 'var(--accent)', fontWeight: 600, textTransform: 'uppercase' }}>{n.consensus}</td>
                          <td>
                            <span className="status-badge status-badge--live">{n.status}</span>
                          </td>
                          <td style={{ textAlign: 'right', color: 'var(--text)', fontWeight: 700 }}>
                            {n.balance !== null ? `${n.balance.toFixed(4)} ⬡` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: Blockchain Ledger */}
        {activeTab === 'blockchain' && (
          <BlockchainExplorer
            blocks={chain?.chain || []}
            totalBlocks={chain?.length || 0}
            currentPage={chainPage}
            pageSize={chainPageSize}
            onPageChange={(p) => setChainPage(p)}
          />
        )}

        {/* Tab 4: Transactions */}
        {activeTab === 'transactions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <TransactionPanel
              availableBalance={availableBalance}
              onTransactionSubmitted={() => {
                apiService.getMempool().then(setMempool).catch(() => {});
              }}
            />
            <MempoolViewer mempool={mempool} />
          </div>
        )}

        {/* Tab 5: Consensus / PoS */}
        {activeTab === 'consensus' && (
          <PoSTelemetryPanel consensus={consensus} stakes={stakes} />
        )}

        {/* Tab 6: Security */}
        {activeTab === 'security' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <SecurityPanel attacks={attacks} />
            <EventConsole events={events} onClear={() => setEvents([])} />
          </div>
        )}

        {/* Tab 7: Attack Lab */}
        {activeTab === 'attack_lab' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <AttackLabPanel
              scenarios={attackScenarios}
              latestAttackEvent={events.find((e) => e.event.startsWith('attack_')) || null}
              onAttackTriggered={loadDashboardData}
            />
            <EventConsole events={events} onClear={() => setEvents([])} />
          </div>
        )}

        {/* Tab 8: Metrics & Analytics */}
        {activeTab === 'analytics' && (
          <MetricsAnalyticsPanel
            metrics={metrics}
            onRefresh={() => apiService.getMetrics().then(setMetrics).catch(() => {})}
            onReset={async () => {
              await apiService.resetMetrics();
              const updated = await apiService.getMetrics();
              setMetrics(updated);
            }}
            isLoading={isRefreshing}
          />
        )}
      </main>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border-subtle)',
          background: 'var(--surface)',
          padding: '10px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="status-dot status-dot--live animate-live" />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            Mission Control Status: Stellar
          </span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-dim)' }}>
          Blockchain Simulation v1.0.0
        </span>
      </footer>

      <NodeInspectorModal
        nodeId={selectedNodeId}
        onClose={() => setSelectedNodeId(null)}
      />
    </div>
  );
}

export default App;
