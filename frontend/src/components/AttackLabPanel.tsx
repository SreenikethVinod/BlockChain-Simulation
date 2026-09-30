import React, { useState } from 'react';
import {
  ShieldAlert,
  Flame,
  Zap,
  GitBranch,
  KeyRound,
  FileX,
  Coins,
  Play,
  RotateCcw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Terminal,
  Activity,
  ChevronRight,
  Eye,
} from 'lucide-react';
import {
  AttackScenarioInfo,
  AttackExecutionResponse,
  AttackTimelineEvent,
} from '../types/api';
import { api } from '../services/api';

interface AttackLabPanelProps {
  scenarios: AttackScenarioInfo[];
  latestAttackEvent: any | null;
  onAttackTriggered?: () => void;
}

const LIFECYCLE_STAGES = ['READY', 'ARMED', 'EXECUTING', 'DETECTED', 'MITIGATED', 'COMPLETE'];

const DEFAULT_SCENARIOS: AttackScenarioInfo[] = [
  {
    id: 'double_sign',
    name: 'Double Signing (Equivocation)',
    description: 'A rogue validator signs two conflicting blocks at the identical chain height. The network detects cryptographic equivocation evidence and slashes the validator\'s stake.',
    supported_consensus: ['pos'],
    parameters: ['malicious_validator', 'target_node'],
    expected_outcome: 'Evidence detected, validator slashed, canonical chain preserved.'
  },
  {
    id: 'double_spend',
    name: 'Double Spend Attempt',
    description: 'Adversary attempts to broadcast two conflicting transactions simultaneously that together exceed the account balance. Validation rules strictly reject the second spend.',
    supported_consensus: ['pos', 'pow', 'poa'],
    parameters: ['amount', 'target_node'],
    expected_outcome: 'First transaction accepted; conflicting spend rejected due to balance exhaustion.'
  },
  {
    id: 'fork',
    name: 'Competing Fork Attack',
    description: 'An adversarial branch is created diverging from the canonical chain. The consensus deterministic fork-choice rule evaluates chain weight and rejects the weaker branch.',
    supported_consensus: ['pos', 'pow'],
    parameters: ['target_node'],
    expected_outcome: 'Fork detected at common ancestor; heaviest chain rule retains canonical branch.'
  },
  {
    id: 'invalid_vrf',
    name: 'Invalid VRF Proof / Lottery Fraud',
    description: 'An unauthorized node proposes a block with a fraudulent or losing VRF output (vrf_output >= threshold or wrong epoch seed). Block validation rejects it immediately.',
    supported_consensus: ['pos'],
    parameters: ['target_node'],
    expected_outcome: 'VRF proof or threshold verification fails; block discarded.'
  },
  {
    id: 'invalid_signature',
    name: 'Invalid Block Signature',
    description: 'An attacker tampers with block contents after signing or submits a forged signature. Real cryptographic ECDSA verification rejects the block.',
    supported_consensus: ['pos', 'pow', 'poa'],
    parameters: ['target_node'],
    expected_outcome: 'ECDSA BadSignatureError caught; block rejected without altering chain.'
  },
  {
    id: 'fake_stake',
    name: 'Fake / Unauthorized Stake',
    description: 'An adversary attempts to claim stake exceeding their wallet balance or injects duplicate stake records. Canonical stake validation blocks the unauthorized claim.',
    supported_consensus: ['pos'],
    parameters: ['amount', 'target_node'],
    expected_outcome: 'Stake claim rejected; canonical validator roster remains unaltered.'
  },
];

export const AttackLabPanel: React.FC<AttackLabPanelProps> = ({
  scenarios,
  onAttackTriggered,
}) => {
  const activeScenarios = scenarios && scenarios.length > 0 ? scenarios : DEFAULT_SCENARIOS;
  const [selectedAttack, setSelectedAttack] = useState<string>('double_sign');
  const [targetNode, setTargetNode] = useState<string>('node1');
  const [maliciousValidator, setMaliciousValidator] = useState<string>('adversary_validator_1');
  const [spendAmount, setSpendAmount] = useState<number>(40);
  const [stakeAmount, setStakeAmount] = useState<number>(1000000);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [activeResponse, setActiveResponse] = useState<AttackExecutionResponse | null>(null);
  const [currentStage, setCurrentStage] = useState<string>('READY');
  const [timeline, setTimeline] = useState<AttackTimelineEvent[]>([]);

  const getScenarioIcon = (id: string) => {
    switch (id) {
      case 'double_sign':
        return <Zap className="w-5 h-5 text-stellar-amber" />;
      case 'double_spend':
        return <Flame className="w-5 h-5 text-stellar-rose" />;
      case 'fork':
        return <GitBranch className="w-5 h-5 text-stellar-cyan" />;
      case 'invalid_vrf':
        return <KeyRound className="w-5 h-5 text-stellar-violet" />;
      case 'invalid_signature':
        return <FileX className="w-5 h-5 text-stellar-rose" />;
      case 'fake_stake':
        return <Coins className="w-5 h-5 text-stellar-amber" />;
      default:
        return <ShieldAlert className="w-5 h-5 text-stellar-cyan" />;
    }
  };

  const handleLaunchAttack = async () => {
    setIsExecuting(true);
    setErrorMsg(null);
    setCurrentStage('ARMED');

    try {
      const payload: any = {
        target_node: targetNode,
      };

      if (selectedAttack === 'double_sign') {
        payload.malicious_validator = maliciousValidator;
      } else if (selectedAttack === 'double_spend') {
        payload.amount = Number(spendAmount);
      } else if (selectedAttack === 'fake_stake') {
        payload.amount = Number(stakeAmount);
      }

      setCurrentStage('EXECUTING');
      const response = await api.executeAttack(selectedAttack, payload);
      setActiveResponse(response);
      setTimeline(response.timeline);

      // Determine final stage
      if (response.status === 'mitigated') {
        setCurrentStage('MITIGATED');
      } else if (response.status === 'rejected') {
        setCurrentStage('REJECTED');
      } else {
        setCurrentStage('COMPLETE');
      }

      if (onAttackTriggered) {
        onAttackTriggered();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Attack execution failed');
      setCurrentStage('READY');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleResetSandbox = () => {
    setActiveResponse(null);
    setTimeline([]);
    setCurrentStage('READY');
    setErrorMsg(null);
  };

  const selectedScenarioInfo = activeScenarios.find((s) => s.id === selectedAttack);

  return (
    <div className="space-y-6">
      {/* 1. Sandbox Restriction Notice */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl border border-stellar-amber/40 bg-stellar-amber/10 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-stellar-amber/20 text-stellar-amber">
            <AlertTriangle className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-stellar-amber/30 text-stellar-amber border border-stellar-amber/50">
                ⚠ ATTACK SIMULATION
              </span>
              <span className="font-mono text-xs font-semibold text-slate-300">
                LOCAL SANDBOX ENFORCED
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              All adversarial scenarios exercise real in-memory consensus validation. No network packets are routed outside this local node constellation.
            </p>
          </div>
        </div>

        <button
          onClick={handleResetSandbox}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-space-600 bg-space-800 hover:bg-space-700 text-xs font-mono text-slate-300 transition-colors self-start sm:self-auto"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset Sandbox
        </button>
      </div>

      {/* 2. Attack Scenario Cards Grid */}
      <div>
        <h3 className="text-sm font-semibold tracking-wider uppercase text-slate-400 mb-3 flex items-center gap-2">
          <Flame className="w-4 h-4 text-stellar-rose" />
          Select Attack Vector
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {activeScenarios.map((scenario) => {
            const isSelected = selectedAttack === scenario.id;
            return (
              <button
                key={scenario.id}
                onClick={() => setSelectedAttack(scenario.id)}
                className={`flex flex-col text-left p-4 rounded border transition-all duration-150 ${
                  isSelected
                    ? 'border-stellar-amber bg-surface-raised'
                    : 'border-space-700/60 bg-space-900/60 hover:border-space-600 hover:bg-space-800/40'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-2">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded bg-space-800 border border-space-700">
                      {getScenarioIcon(scenario.id)}
                    </div>
                    <span className="font-semibold text-sm text-slate-200">
                      {scenario.name}
                    </span>
                  </div>
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-stellar-amber" />
                  )}
                </div>
                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  {scenario.description}
                </p>
                <div className="mt-3 pt-2.5 border-t border-space-800 flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span>Engine: {scenario.supported_consensus.join(', ').toUpperCase()}</span>
                  <span className="text-stellar-emerald flex items-center gap-1">
                    Ready <ChevronRight className="w-3 h-3" />
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. Parameter Configuration & Launch Control */}
      {selectedScenarioInfo && (
        <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-space-700/60">
            <div>
              <h4 className="text-base font-bold text-slate-100 flex items-center gap-2">
                {getScenarioIcon(selectedScenarioInfo.id)}
                {selectedScenarioInfo.name}
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                {selectedScenarioInfo.description}
              </p>
            </div>
            <div className="text-xs font-mono px-3 py-1 rounded-md bg-space-800 border border-space-700 text-slate-300 self-start sm:self-auto">
              Expected: <span className="text-stellar-emerald">{selectedScenarioInfo.expected_outcome}</span>
            </div>
          </div>

          {/* Config Inputs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-1">
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">
                Target Node / Cluster
              </label>
              <input
                type="text"
                value={targetNode}
                onChange={(e) => setTargetNode(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-space-950 border border-space-700 font-mono text-xs text-slate-200 focus:outline-none focus:border-stellar-cyan"
                placeholder="e.g. node1"
              />
            </div>

            {selectedAttack === 'double_sign' && (
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Malicious Validator Alias
                </label>
                <input
                  type="text"
                  value={maliciousValidator}
                  onChange={(e) => setMaliciousValidator(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-space-950 border border-space-700 font-mono text-xs text-slate-200 focus:outline-none focus:border-stellar-cyan"
                />
              </div>
            )}

            {selectedAttack === 'double_spend' && (
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Spend Amount (Each Transaction)
                </label>
                <input
                  type="number"
                  value={spendAmount}
                  onChange={(e) => setSpendAmount(Number(e.target.value))}
                  min="0.1"
                  step="0.1"
                  className="w-full px-3 py-2 rounded-lg bg-space-950 border border-space-700 font-mono text-xs text-slate-200 focus:outline-none focus:border-stellar-cyan"
                />
              </div>
            )}

            {selectedAttack === 'fake_stake' && (
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Claimed Stake Amount
                </label>
                <input
                  type="number"
                  value={stakeAmount}
                  onChange={(e) => setStakeAmount(Number(e.target.value))}
                  min="1"
                  className="w-full px-3 py-2 rounded-lg bg-space-950 border border-space-700 font-mono text-xs text-slate-200 focus:outline-none focus:border-stellar-cyan"
                />
              </div>
            )}
          </div>

          {/* Action Trigger */}
          <div className="flex items-center gap-4 pt-2">
            <button
              onClick={handleLaunchAttack}
              disabled={isExecuting}
              className="btn btn--danger"
              style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', fontSize: '0.75rem', fontWeight: 700 }}
            >
              {isExecuting ? (
                <>
                  <div className="w-3.5 h-3.5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                  Executing Sandbox Simulation...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  Execute Attack Scenario
                </>
              )}
            </button>

            {errorMsg && (
              <span className="text-xs font-mono text-stellar-rose flex items-center gap-1.5">
                <XCircle className="w-4 h-4" /> {errorMsg}
              </span>
            )}
          </div>
        </div>
      )}

      {/* 4. Attack Lifecycle Stepper */}
      <div className="panel" style={{ padding: '16px' }}>
        <h4 className="text-xs font-mono uppercase text-slate-400 mb-3 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-stellar-cyan" />
          Attack Execution Lifecycle
        </h4>
        <div className="grid grid-cols-6 gap-2">
          {LIFECYCLE_STAGES.map((stage, idx) => {
            const isActive = currentStage === stage;
            const isPassed =
              LIFECYCLE_STAGES.indexOf(currentStage) >= idx && currentStage !== 'READY';

            return (
              <div
                key={stage}
                className={`flex flex-col items-center justify-center p-2.5 rounded border text-center transition-all ${
                  isActive
                    ? 'border-stellar-amber bg-space-800 text-stellar-amber font-bold'
                    : isPassed
                    ? 'border-stellar-emerald/40 bg-stellar-emerald/10 text-stellar-emerald'
                    : 'border-space-800 bg-space-950/60 text-slate-600'
                }`}
              >
                <span className="text-[10px] font-mono text-slate-500 mb-0.5">
                  0{idx + 1}
                </span>
                <span className="font-mono text-xs tracking-wider">{stage}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 5. Live Timeline & Evidence Result Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline Log */}
        <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', height: 400 }}>
          <h4 className="text-sm font-semibold text-slate-200 mb-3 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-stellar-cyan" />
              Real-Time Attack Timeline
            </span>
            <span className="text-xs font-mono text-slate-500">
              {timeline.length} Recorded Steps
            </span>
          </h4>

          <div className="flex-1 overflow-y-auto space-y-2.5 pr-2 font-mono text-xs">
            {timeline.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 italic">
                <ShieldAlert className="w-8 h-8 mb-2 stroke-1 opacity-50" />
                Select a vector above and click "Execute Attack Scenario" to observe live telemetry.
              </div>
            ) : (
              timeline.map((item, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-space-950 border border-space-800 flex items-start gap-2.5 animate-in fade-in duration-200"
                >
                  <span className="text-slate-500 text-[11px] shrink-0">{item.time_str}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold shrink-0 ${
                      item.stage === 'MITIGATED' || item.stage === 'COMPLETE'
                        ? 'bg-stellar-emerald/20 text-stellar-emerald'
                        : item.stage === 'DETECTED' || item.stage === 'REJECTED'
                        ? 'bg-stellar-rose/20 text-stellar-rose'
                        : item.stage === 'EXECUTING' || item.stage === 'ARMED'
                        ? 'bg-stellar-amber/20 text-stellar-amber'
                        : 'bg-space-800 text-slate-400'
                    }`}
                  >
                    {item.stage}
                  </span>
                  <span className="text-slate-300 break-words flex-1">{item.message}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Forensic Evidence & Network Response */}
        <div className="panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', height: 400 }}>
          <h4 className="text-sm font-semibold text-slate-200 mb-3 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Eye className="w-4 h-4 text-stellar-emerald" />
              Forensic Evidence & Consensus Verdict
            </span>
            {activeResponse && (
              <span
                className={`text-xs font-mono px-2 py-0.5 rounded uppercase font-bold ${
                  activeResponse.status === 'mitigated'
                    ? 'bg-stellar-emerald/20 text-stellar-emerald border border-stellar-emerald/40'
                    : activeResponse.status === 'rejected'
                    ? 'bg-stellar-rose/20 text-stellar-rose border border-stellar-rose/40'
                    : 'bg-stellar-amber/20 text-stellar-amber border border-stellar-amber/40'
                }`}
              >
                Verdict: {activeResponse.status}
              </span>
            )}
          </h4>

          <div className="flex-1 overflow-y-auto space-y-3 pr-2">
            {!activeResponse ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 italic font-mono text-xs">
                No active attack execution. Awaiting simulation trigger.
              </div>
            ) : (
              <>
                {/* Network Verdict Summary */}
                <div className="p-3 rounded-lg bg-space-950 border border-space-700/60">
                  <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                    Consensus Network Response
                  </div>
                  <div className="text-sm font-semibold text-stellar-cyan flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-stellar-emerald shrink-0" />
                    {activeResponse.network_response}
                  </div>
                </div>

                {/* Forensic Evidence Key-Values */}
                <div className="p-3 rounded-lg bg-space-950 border border-space-700/60 space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1 flex items-center justify-between">
                    <span>Forensic Cryptographic Evidence</span>
                    <span className="text-[10px] text-stellar-amber">Zero Secrets Handled</span>
                  </div>
                  <div className="space-y-1.5 font-mono text-xs">
                    {Object.entries(activeResponse.evidence || {}).map(([k, v]) => (
                      <div key={k} className="flex flex-col sm:flex-row sm:items-start justify-between gap-1 py-1 border-b border-space-900 last:border-0">
                        <span className="text-slate-400 capitalize">{k.replace(/_/g, ' ')}:</span>
                        <span className="text-slate-200 text-right truncate max-w-xs font-mono" title={String(v)}>
                          {typeof v === 'boolean' ? (
                            v ? (
                              <span className="text-stellar-emerald">TRUE</span>
                            ) : (
                              <span className="text-stellar-rose">FALSE</span>
                            )
                          ) : (
                            String(v)
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Canonical Ledger State Result */}
                <div className="p-3 rounded-lg bg-space-950 border border-space-700/60 font-mono text-xs">
                  <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                    Resulting Canonical State
                  </div>
                  <div className="space-y-1 text-slate-300">
                    {Object.entries(activeResponse.final_state || {}).map(([k, v]) => (
                      <div key={k} className="flex justify-between py-0.5">
                        <span className="text-slate-400">{k}:</span>
                        <span className="text-stellar-emerald truncate max-w-xs">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
