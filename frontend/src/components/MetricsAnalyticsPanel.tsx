import React, { useState } from 'react';
import {
  Activity,
  BarChart2,
  Clock,
  Layers,
  ShieldCheck,
  RotateCcw,
  RefreshCw,
  Cpu,
  Inbox,
  AlertTriangle,
  Zap,
  TrendingUp,
  Radio,
  Server
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell
} from 'recharts';
import { MetricsOverviewResponse } from '../types/api';

interface MetricsAnalyticsPanelProps {
  metrics: MetricsOverviewResponse | null;
  onRefresh: () => void;
  onReset: () => Promise<void>;
  isLoading?: boolean;
}

export const MetricsAnalyticsPanel: React.FC<MetricsAnalyticsPanelProps> = ({
  metrics,
  onRefresh,
  onReset,
  isLoading = false,
}) => {
  const [isResetting, setIsResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);

  const handleResetClick = async () => {
    if (!window.confirm('Reset observational telemetry buffers? (Canonical blockchain state will remain untouched)')) {
      return;
    }
    setIsResetting(true);
    setResetMessage(null);
    try {
      await onReset();
      setResetMessage('Telemetry history and counters reset successfully.');
      setTimeout(() => setResetMessage(null), 4000);
    } catch (err: any) {
      setResetMessage(`Reset failed: ${err.message}`);
    } finally {
      setIsResetting(false);
    }
  };

  // Helper formatting functions ensuring no NaN or crashes
  const formatTime = (ts: number): string => {
    if (!ts || !Number.isFinite(ts)) return '--:--:--';
    try {
      const d = new Date(ts * 1000);
      return d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return '--:--:--';
    }
  };

  const sanitizeNumber = (val: any, fallback = 0): number => {
    if (typeof val === 'number' && Number.isFinite(val)) return val;
    return fallback;
  };

  // Prepare TPS timeseries
  const rawTps = metrics?.transactions?.history_tps || [];
  const tpsChartData = rawTps
    .filter((p) => p && Number.isFinite(p.timestamp) && Number.isFinite(p.value))
    .slice()
    .sort((a, b) => a.timestamp - b.timestamp)
    .map((p) => ({
      time: formatTime(p.timestamp),
      tps: sanitizeNumber(p.value),
    }));

  // Prepare Block Interval data
  const rawIntervals = metrics?.blockchain?.history_block_intervals || [];
  const intervalChartData = rawIntervals
    .filter((p) => p && Number.isFinite(p.value))
    .map((p, idx) => ({
      index: `#${idx + 1}`,
      interval: sanitizeNumber(p.value),
      time: formatTime(p.timestamp),
    }));

  // Prepare Mempool depth timeseries
  const rawMempool = metrics?.mempool?.history_mempool_depth || [];
  const mempoolChartData = rawMempool
    .filter((p) => p && Number.isFinite(p.timestamp) && Number.isFinite(p.value))
    .slice()
    .sort((a, b) => a.timestamp - b.timestamp)
    .map((p) => ({
      time: formatTime(p.timestamp),
      depth: sanitizeNumber(p.value),
    }));

  // Prepare Stake distribution data
  const stakeDist = metrics?.consensus?.pos?.stake_distribution || [];
  const stakeChartData = stakeDist.map((s) => ({
    name: s.name || s.staker.slice(0, 10),
    stake: sanitizeNumber(s.stake),
    percentage: sanitizeNumber(s.percentage),
  }));

  // Prepare Attack Outcomes data (Phase 7 integration)
  const attacksByType = metrics?.security?.attacks_by_type || {};
  const attackTypes = ['double_sign', 'double_spend', 'fork', 'invalid_vrf', 'invalid_signature', 'fake_stake'];
  const attackChartData = attackTypes.map((t) => ({
    type: t.replace('_', ' ').toUpperCase(),
    attempts: sanitizeNumber(attacksByType[t]),
  }));
  const totalAttacksCount = metrics?.security?.total_attack_attempts || 0;

  const isStandalone = metrics?.is_standalone ?? true;

  return (
    <div className="space-y-6" data-testid="metrics-analytics-panel">
      {/* 1. Header & Operational Control Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-space-800 p-4 rounded-lg border border-space-700 shadow-md">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
            <Activity className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold tracking-wider text-space-100 uppercase">
                Real-Time Telemetry & Analytics
              </h2>
              {/* Simulation Mode Badge */}
              {isStandalone ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-950/60 border border-amber-800/60 text-amber-300">
                  <Server className="w-3 h-3 mr-1" />
                  STANDALONE OBSERVATION MODE
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950/60 border border-emerald-800/60 text-emerald-300">
                  <Radio className="w-3 h-3 mr-1 animate-pulse" />
                  LIVE SIMULATION TELEMETRY
                </span>
              )}
            </div>
            <p className="text-xs text-space-400 mt-0.5">
              Mission Control Phase 8 • Sliding Bounded In-Memory Telemetry Pipeline
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-space-700 hover:bg-space-600 text-space-200 text-xs font-medium transition border border-space-600 disabled:opacity-50"
            title="Refresh current metrics snapshot"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={handleResetClick}
            disabled={isResetting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-xs font-medium transition border border-rose-800/50 disabled:opacity-50"
            title="Reset sliding history and counters without altering blockchain state"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
            Reset Telemetry
          </button>
        </div>
      </div>

      {resetMessage && (
        <div className="p-3 rounded bg-space-800/90 border border-cyan-800/50 text-cyan-300 text-xs flex items-center gap-2">
          <Zap className="w-4 h-4 text-cyan-400" />
          <span>{resetMessage}</span>
        </div>
      )}

      {/* 2. KPI Summary Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Block Height */}
        <div className="bg-space-800 p-3.5 rounded-lg border border-space-700">
          <div className="flex items-center justify-between text-space-400 text-xs mb-1">
            <span>Block Height</span>
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-xl font-bold font-mono text-space-100">
            {metrics?.blockchain?.block_height ?? 0}
          </div>
          <div className="text-[10px] text-space-400 mt-1">
            Total Observed: {metrics?.blockchain?.total_blocks_observed ?? 0}
          </div>
        </div>

        {/* Real-Time TPS */}
        <div className="bg-space-800 p-3.5 rounded-lg border border-space-700">
          <div className="flex items-center justify-between text-space-400 text-xs mb-1">
            <span>Current TPS</span>
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold font-mono text-emerald-400">
            {metrics?.transactions?.current_tps !== null && metrics?.transactions?.current_tps !== undefined
              ? `${metrics.transactions.current_tps.toFixed(2)}`
              : '0.00'}
          </div>
          <div className="text-[10px] text-space-400 mt-1">
            Confirmed: {metrics?.transactions?.transactions_confirmed ?? 0}
          </div>
        </div>

        {/* Mempool Depth */}
        <div className="bg-space-800 p-3.5 rounded-lg border border-space-700">
          <div className="flex items-center justify-between text-space-400 text-xs mb-1">
            <span>Mempool Depth</span>
            <Inbox className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-xl font-bold font-mono text-amber-300">
            {metrics?.mempool?.current_mempool_size ?? 0}
          </div>
          <div className="text-[10px] text-space-400 mt-1">
            Entered: {metrics?.mempool?.transactions_entered_mempool_total ?? 0}
          </div>
        </div>

        {/* Avg Block Interval */}
        <div className="bg-space-800 p-3.5 rounded-lg border border-space-700">
          <div className="flex items-center justify-between text-space-400 text-xs mb-1">
            <span>Avg Interval</span>
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="text-xl font-bold font-mono text-indigo-300">
            {metrics?.blockchain?.average_block_interval_seconds !== null && metrics?.blockchain?.average_block_interval_seconds !== undefined
              ? `${metrics.blockchain.average_block_interval_seconds.toFixed(1)}s`
              : 'N/A'}
          </div>
          <div className="text-[10px] text-space-400 mt-1">
            BPM: {metrics?.blockchain?.blocks_per_minute ?? 0}
          </div>
        </div>

        {/* Active Nodes / Peers */}
        <div className="bg-space-800 p-3.5 rounded-lg border border-space-700">
          <div className="flex items-center justify-between text-space-400 text-xs mb-1">
            <span>Peers / Nodes</span>
            <Server className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-xl font-bold font-mono text-cyan-300">
            {metrics?.network?.connected_peers ?? 0} / {metrics?.network?.active_nodes ?? 0}
          </div>
          <div className="text-[10px] text-space-400 mt-1">
            Joins: {metrics?.network?.peer_joins_total ?? 0} | Leaves: {metrics?.network?.peer_leaves_total ?? 0}
          </div>
        </div>

        {/* Attack Mitigation Rate */}
        <div className="bg-space-800 p-3.5 rounded-lg border border-space-700">
          <div className="flex items-center justify-between text-space-400 text-xs mb-1">
            <span>Mitigation Rate</span>
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold font-mono text-emerald-400">
            {metrics?.security?.mitigation_rate_pct !== null && metrics?.security?.mitigation_rate_pct !== undefined
              ? `${metrics.security.mitigation_rate_pct.toFixed(1)}%`
              : 'N/A'}
          </div>
          <div className="text-[10px] text-space-400 mt-1">
            Attacks: {metrics?.security?.total_attack_attempts ?? 0}
          </div>
        </div>
      </div>

      {/* 3. Primary Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Real-Time TPS Over Time */}
        <div className="bg-space-800 p-4 rounded-lg border border-space-700 shadow-md">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-space-100 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                Authentic Transaction Throughput (TPS)
              </h3>
              <p className="text-xs text-space-400">Sliding 10-second rolling window across confirmed transactions</p>
            </div>
          </div>
          <div className="h-56 w-full flex items-center justify-center">
            {tpsChartData.length === 0 ? (
              <div className="text-center text-xs text-space-400">
                <Activity className="w-8 h-8 text-space-600 mx-auto mb-1 animate-pulse" />
                Insufficient telemetry data (No transactions confirmed yet)
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={tpsChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#262933" />
                  <XAxis dataKey="time" stroke="#71788e" fontSize={10} tickLine={false} />
                  <YAxis stroke="#71788e" fontSize={10} tickLine={false} domain={[0, 'auto']} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#181a20', borderColor: '#2e3342', fontSize: '11px' }}
                    labelStyle={{ color: '#a0aec0' }}
                  />
                  <Line type="monotone" dataKey="tps" name="TPS" stroke="#10b981" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Chart 2: Block Production Intervals */}
        <div className="bg-space-800 p-4 rounded-lg border border-space-700 shadow-md">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-space-100 flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                Block Confirmation Intervals (Seconds)
              </h3>
              <p className="text-xs text-space-400">Real timestamp deltas between consecutive confirmed blocks</p>
            </div>
          </div>
          <div className="h-56 w-full flex items-center justify-center">
            {intervalChartData.length === 0 ? (
              <div className="text-center text-xs text-space-400">
                <Layers className="w-8 h-8 text-space-600 mx-auto mb-1" />
                Insufficient block intervals (Requires ≥ 2 confirmed blocks)
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={intervalChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#262933" />
                  <XAxis dataKey="index" stroke="#71788e" fontSize={10} tickLine={false} />
                  <YAxis stroke="#71788e" fontSize={10} tickLine={false} domain={[0, 'auto']} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#181a20', borderColor: '#2e3342', fontSize: '11px' }}
                    formatter={(val: any) => [`${val}s`, 'Interval']}
                  />
                  <Bar dataKey="interval" fill="#06b6d4" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Chart 3: Mempool Depth Trajectory */}
        <div className="bg-space-800 p-4 rounded-lg border border-space-700 shadow-md">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-space-100 flex items-center gap-2">
                <Inbox className="w-4 h-4 text-amber-400" />
                Mempool Depth History
              </h3>
              <p className="text-xs text-space-400">Chronological trajectory of unconfirmed transaction backlog</p>
            </div>
          </div>
          <div className="h-56 w-full flex items-center justify-center">
            {mempoolChartData.length === 0 ? (
              <div className="text-center text-xs text-space-400">
                <Inbox className="w-8 h-8 text-space-600 mx-auto mb-1" />
                No mempool samples recorded
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mempoolChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#262933" />
                  <XAxis dataKey="time" stroke="#71788e" fontSize={10} tickLine={false} />
                  <YAxis stroke="#71788e" fontSize={10} tickLine={false} domain={[0, 'auto']} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#181a20', borderColor: '#2e3342', fontSize: '11px' }}
                    labelStyle={{ color: '#a0aec0' }}
                  />
                  <Area type="monotone" dataKey="depth" name="Pending Txs" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.15} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Chart 4: Consensus Stake Distribution */}
        <div className="bg-space-800 p-4 rounded-lg border border-space-700 shadow-md">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-space-100 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-indigo-400" />
                Proof-of-Stake Validator Distribution
              </h3>
              <p className="text-xs text-space-400">Stake percentage weight per verified validator</p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-space-700 text-space-300">
              {metrics?.consensus?.consensus_type?.toUpperCase() || 'POS'}
            </span>
          </div>
          <div className="h-56 w-full flex items-center justify-center">
            {metrics?.consensus?.consensus_type !== 'pos' ? (
              <div className="text-center text-xs text-space-400">
                <Server className="w-8 h-8 text-space-600 mx-auto mb-1" />
                Consensus is {metrics?.consensus?.consensus_type?.toUpperCase()} — Staking metrics not applicable.
              </div>
            ) : stakeChartData.length === 0 ? (
              <div className="text-center text-xs text-space-400">
                <Cpu className="w-8 h-8 text-space-600 mx-auto mb-1" />
                No active stakers recorded in current epoch.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stakeChartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#262933" />
                  <XAxis type="number" stroke="#71788e" fontSize={10} tickLine={false} unit="%" />
                  <YAxis type="category" dataKey="name" stroke="#71788e" fontSize={10} tickLine={false} width={80} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#181a20', borderColor: '#2e3342', fontSize: '11px' }}
                    formatter={(val: any, name: any, item: any) => [`${val}% (${item.payload.stake} coins)`, 'Stake Weight']}
                  />
                  <Bar dataKey="percentage" fill="#6366f1" radius={[0, 3, 3, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* 4. Security & Attack Lab Telemetry (Phase 7 Integration) */}
      <div className="bg-space-800 p-4 rounded-lg border border-space-700 shadow-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="text-sm font-semibold text-space-100 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-rose-400" />
              Security & Attack Lab Forensic Metrics
            </h3>
            <p className="text-xs text-space-400">
              Aggregated adversarial execution records: attempts, detections, mitigations, and canonical ledger protection
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="text-space-400">
              Preserved Ledger States: <strong className="text-emerald-400 font-mono">{metrics?.security?.canonical_chain_preserved_count ?? 0}</strong>
            </span>
            <span className="text-space-400">
              Total Attempts: <strong className="text-space-100 font-mono">{totalAttacksCount}</strong>
            </span>
          </div>
        </div>

        {totalAttacksCount === 0 ? (
          <div className="p-8 text-center border border-dashed border-space-700 rounded-lg text-xs text-space-400">
            <AlertTriangle className="w-8 h-8 text-space-600 mx-auto mb-2" />
            No adversarial attacks executed in current session. Execute scenarios in Attack Lab to observe telemetry.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            {/* Attack attempts chart */}
            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={attackChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#262933" />
                  <XAxis dataKey="type" stroke="#71788e" fontSize={9} tickLine={false} interval={0} />
                  <YAxis stroke="#71788e" fontSize={10} tickLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ backgroundColor: '#181a20', borderColor: '#2e3342', fontSize: '11px' }} />
                  <Bar dataKey="attempts" name="Attempts" fill="#f43f5e" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Metrics Breakdown Stats */}
            <div className="space-y-3 bg-space-900/60 p-4 rounded border border-space-700/60">
              <div className="flex justify-between items-center text-xs">
                <span className="text-space-400">Adversarial Attempts Executed:</span>
                <span className="font-mono font-bold text-space-100">{metrics?.security?.total_attack_attempts ?? 0}</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-space-400">Cryptographically Detected:</span>
                <span className="font-mono font-bold text-cyan-400">{metrics?.security?.detected_attacks ?? 0}</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-space-400">Consensus Mitigated / Slashed:</span>
                <span className="font-mono font-bold text-emerald-400">{metrics?.security?.mitigated_attacks ?? 0}</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-space-400">Mempool / Chain Rejected:</span>
                <span className="font-mono font-bold text-amber-400">{metrics?.security?.rejected_attacks ?? 0}</span>
              </div>
              <div className="flex justify-between items-center text-xs pt-2 border-t border-space-800">
                <span className="text-space-300 font-semibold">Overall Mitigation Ratio:</span>
                <span className="font-mono font-bold text-emerald-400">
                  {metrics?.security?.mitigation_rate_pct !== null && metrics?.security?.mitigation_rate_pct !== undefined
                    ? `${metrics.security.mitigation_rate_pct.toFixed(1)}%`
                    : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 5. Recent Security Incidents Audit Trail */}
      {metrics?.security?.recent_security_incidents && metrics.security.recent_security_incidents.length > 0 && (
        <div className="bg-space-800 p-4 rounded-lg border border-space-700 shadow-md">
          <h3 className="text-sm font-semibold text-space-100 mb-3 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            Recent Security & Forensic Incident Trail
          </h3>
          <div className="overflow-x-auto max-h-48 overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-space-900/80 text-space-400 sticky top-0">
                <tr>
                  <th className="py-2 px-3">Time</th>
                  <th className="py-2 px-3">Type</th>
                  <th className="py-2 px-3">Stage / Outcome</th>
                  <th className="py-2 px-3">Audit Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-space-700/50 font-mono text-space-200">
                {metrics.security.recent_security_incidents.slice(-15).reverse().map((inc, i) => (
                  <tr key={i} className="hover:bg-space-700/30">
                    <td className="py-1.5 px-3 text-space-400">{formatTime(inc.timestamp || inc.time)}</td>
                    <td className="py-1.5 px-3 uppercase text-cyan-400">{inc.attack_type || inc.type || 'INCIDENT'}</td>
                    <td className="py-1.5 px-3">
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-space-700 text-space-300">
                        {inc.stage || 'VERIFIED'}
                      </span>
                    </td>
                    <td className="py-1.5 px-3 text-space-400 truncate max-w-xs">
                      {JSON.stringify(inc.details || inc.reason || {})}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
