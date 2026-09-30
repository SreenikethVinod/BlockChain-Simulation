import React from 'react';
import { 
  KeyRound, 
  Cpu, 
  Clock, 
  Award, 
  ShieldCheck, 
  BarChart3, 
  AlertCircle 
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  Cell 
} from 'recharts';
import { ConsensusStatusResponse, StakesResponse } from '../types/api';

interface PoSTelemetryPanelProps {
  consensus: ConsensusStatusResponse | null;
  stakes: StakesResponse | null;
}

export const PoSTelemetryPanel: React.FC<PoSTelemetryPanelProps> = ({
  consensus,
  stakes,
}) => {
  const consensusType = consensus?.consensus_type?.toLowerCase() || 'pos';
  const isPoS = consensusType === 'pos';

  const validators = consensus?.validators || [];
  const epochSeed = consensus?.epoch_seed || 'N/A';
  const isEligible = consensus?.eligibility_status;
  const totalStake = consensus?.total_stake || stakes?.total_staked || 0;
  const epochRemaining = stakes?.epoch_remaining_seconds;

  // Prepare data for stake distribution chart from real backend values
  const chartData = validators.map((v, i) => ({
    name: v.staker.includes('BEGIN') ? `Validator ${i + 1}` : v.staker.slice(0, 10),
    stake: v.staked_amount,
    isLocal: v.is_local,
  }));

  const COLORS = ['#00f0ff', '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b'];

  if (!isPoS) {
    return (
      <div className="panel" style={{ padding: '24px', margin: '24px 0', textAlign: 'center' }}>
        <Cpu className="w-10 h-10 text-stellar-violet mx-auto mb-3" />
        <h3 className="text-base font-bold text-white font-sans uppercase">
          Active Consensus Engine: {consensusType.toUpperCase()}
        </h3>
        <p className="text-xs text-slate-400 font-mono-tech mt-2 max-w-lg mx-auto">
          Proof-of-Stake telemetry is currently inactive. This node is participating in {consensusType.toUpperCase()} consensus.
        </p>
      </div>
    );
  }

  return (
    <div className="panel" style={{ padding: '20px', margin: '24px 0', display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-space-700/60 gap-3">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-white font-sans flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-stellar-blue" />
            Proof-of-Stake Consensus & VRF Telemetry
          </h2>
          <p className="text-xs text-slate-400 font-mono-tech mt-0.5">
            Stake-weighted VRF cryptographic lottery determining epoch block proposition eligibility.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono-tech">
          <span className="px-2.5 py-1 rounded bg-space-800 border border-space-700 text-slate-300">
            Total Staked: <strong className="text-stellar-blue">{totalStake} ⬡</strong>
          </span>
        </div>
      </div>

      {/* Epoch Metrics Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono-tech">
        {/* Epoch Seed */}
        <div className="p-3 rounded bg-space-950 border border-space-800">
          <span className="text-slate-500 block mb-1">CANONICAL EPOCH SEED</span>
          <span className="text-stellar-cyan font-bold break-all select-all text-[11px]" title={epochSeed}>
            {epochSeed}
          </span>
        </div>

        {/* VRF Eligibility Status */}
        <div className="p-3 rounded bg-space-950 border border-space-800">
          <span className="text-slate-500 block mb-1">LOCAL NODE VRF ELIGIBILITY</span>
          <div className="flex items-center gap-2">
            {isEligible === true ? (
              <span className="text-stellar-emerald font-semibold flex items-center gap-1.5">
                <Award className="w-4 h-4 text-stellar-emerald" />
                ELIGIBLE FOR NEXT BLOCK
              </span>
            ) : isEligible === false ? (
              <span className="text-slate-400 flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 text-slate-500" />
                INELIGIBLE (BELOW THRESHOLD)
              </span>
            ) : (
              <span className="text-slate-500">STANDBY / NON-STAKER</span>
            )}
          </div>
        </div>

        {/* Epoch Countdown */}
        <div className="p-3 rounded bg-space-950 border border-space-800">
          <span className="text-slate-500 block mb-1">EPOCH TIMING REMAINING</span>
          <div className="flex items-center gap-2 text-white font-semibold">
            <Clock className="w-4 h-4 text-stellar-amber" />
            <span>
              {epochRemaining !== undefined && epochRemaining !== null
                ? `${epochRemaining.toFixed(1)}s until epoch transition`
                : 'Active Epoch Cycle'}
            </span>
          </div>
        </div>
      </div>

      {/* Validator Roster & Stake Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Validator Roster */}
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-1.5 font-mono-tech">
            <ShieldCheck className="w-4 h-4 text-stellar-cyan" />
            Active Validator Roster ({validators.length})
          </h3>

          {validators.length === 0 ? (
            <div 
              data-testid="validators-empty-state"
              className="p-6 rounded bg-space-950/60 border border-space-800 text-slate-500 text-center text-xs font-mono-tech"
            >
              No validators detected in current epoch.
            </div>
          ) : (
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {validators.map((val, idx) => (
                <div 
                  key={`val-${idx}`} 
                  className={`p-3 rounded border text-xs font-mono-tech flex items-center justify-between ${
                    val.is_local 
                      ? 'bg-stellar-cyan/10 border-stellar-cyan/30' 
                      : 'bg-space-950 border-space-850'
                  }`}
                >
                  <div className="truncate max-w-[200px]">
                    <span className="text-white font-semibold block truncate">
                      {val.is_local ? 'Local Validator (This Node)' : `Validator #${idx + 1}`}
                    </span>
                    <span className="text-[10px] text-slate-500 truncate block">
                      {val.staker.slice(0, 30)}...
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-stellar-blue font-bold text-sm block">
                      {val.staked_amount} ⬡
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {totalStake > 0 ? `${((val.staked_amount / totalStake) * 100).toFixed(1)}% Weight` : '0%'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Stake Distribution Chart */}
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-1.5 font-mono-tech">
            <BarChart3 className="w-4 h-4 text-stellar-emerald" />
            Consensus Stake Weight Distribution
          </h3>

          {chartData.length === 0 ? (
            <div className="p-6 rounded bg-space-950/60 border border-space-800 text-slate-500 text-center text-xs font-mono-tech">
              No stake distribution data available.
            </div>
          ) : (
            <div className="p-3 rounded bg-space-950 border border-space-800 h-56 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} fontFamily="monospace" />
                  <YAxis stroke="#64748b" fontSize={10} fontFamily="monospace" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0a1024', borderColor: '#2c4278', fontSize: '11px', fontFamily: 'monospace' }}
                    itemStyle={{ color: '#00f0ff' }}
                  />
                  <Bar dataKey="stake" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
