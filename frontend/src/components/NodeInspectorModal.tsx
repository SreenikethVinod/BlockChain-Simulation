import React, { useEffect, useState } from 'react';
import { 
  X, 
  Server, 
  Key, 
  Coins, 
  ShieldCheck, 
  Wifi, 
  Copy, 
  Check, 
  Cpu, 
  Terminal 
} from 'lucide-react';
import { NodeDetailResponse } from '../types/api';
import { apiService } from '../services/api';

interface NodeInspectorModalProps {
  nodeId: string | null;
  onClose: () => void;
}

export const NodeInspectorModal: React.FC<NodeInspectorModalProps> = ({
  nodeId,
  onClose,
}) => {
  const [node, setNode] = useState<NodeDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  useEffect(() => {
    if (!nodeId) {
      setNode(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    apiService.getNode(nodeId)
      .then((data) => {
        if (isMounted) setNode(data);
      })
      .catch((err) => {
        if (isMounted) setError(err.message || 'Failed to inspect vessel telemetry.');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [nodeId]);

  if (!nodeId) return null;

  const handleCopyKey = () => {
    if (node?.public_key) {
      navigator.clipboard.writeText(node.public_key);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  return (
    <div 
      data-testid="node-inspector-modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div 
        className="panel"
        style={{ width: '100%', maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto', padding: '24px', position: 'relative', background: 'var(--surface)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg hover:bg-space-800 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 pb-4 border-b border-space-800">
          <div className="w-10 h-10 rounded-lg bg-stellar-cyan/10 border border-stellar-cyan/30 flex items-center justify-center text-stellar-cyan">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-white font-sans">
                {node?.name || nodeId}
              </h3>
              {node?.is_self && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-stellar-cyan/20 border border-stellar-cyan/40 text-stellar-cyan font-mono-tech">
                  LOCAL HOST VESSEL
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 font-mono-tech">
              Node ID: {node?.node_id || nodeId}
            </p>
          </div>
        </div>

        {/* Content Body */}
        {loading ? (
          <div className="py-12 text-center text-slate-400 font-mono-tech animate-pulse">
            Querying node telemetry from station...
          </div>
        ) : error ? (
          <div className="py-8 text-center text-stellar-rose font-mono-tech text-xs">
            {error}
          </div>
        ) : node ? (
          <div className="space-y-4 pt-4 text-xs font-mono-tech">
            {/* Grid of Attributes */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-2.5 rounded bg-space-950/70 border border-space-800">
                <span className="text-slate-500 block mb-1">OPERATIONAL STATUS</span>
                <span className="text-stellar-emerald font-semibold uppercase flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-stellar-emerald animate-ping" />
                  {node.status}
                </span>
              </div>

              <div className="p-2.5 rounded bg-space-950/70 border border-space-800">
                <span className="text-slate-500 block mb-1">CONSENSUS ENGINE</span>
                <span className="text-stellar-violet font-semibold uppercase flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5" />
                  {node.consensus}
                </span>
              </div>

              <div className="p-2.5 rounded bg-space-950/70 border border-space-800">
                <span className="text-slate-500 block mb-1">P2P ENDPOINT</span>
                <span className="text-white font-semibold">
                  {node.host}:{node.port}
                </span>
              </div>

              <div className="p-2.5 rounded bg-space-950/70 border border-space-800">
                <span className="text-slate-500 block mb-1">ACCOUNT BALANCE</span>
                <span className="text-stellar-cyan font-semibold flex items-center gap-1">
                  <Coins className="w-3.5 h-3.5" />
                  {node.balance !== null ? `${node.balance.toFixed(4)} ⬡` : 'N/A'}
                </span>
              </div>
            </div>

            {/* Stake / Validator Info */}
            {node.staked_amount !== undefined && node.staked_amount !== null && (
              <div className="p-2.5 rounded bg-space-950/70 border border-space-800 flex items-center justify-between">
                <div>
                  <span className="text-slate-500 block mb-0.5">CURRENT EPOCH STAKE</span>
                  <span className="text-white font-semibold">{node.staked_amount} coins staked</span>
                </div>
                <span className="px-2 py-1 rounded bg-stellar-blue/20 border border-stellar-blue/40 text-stellar-blue text-[10px]">
                  ACTIVE VALIDATOR
                </span>
              </div>
            )}

            {/* Public Key (Safe, Never Private Key) */}
            <div className="p-3 rounded bg-space-950 border border-space-800">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-slate-400 font-semibold flex items-center gap-1.5">
                  <Key className="w-3.5 h-3.5 text-stellar-cyan" />
                  Public Key (ECDSA SECP256k1)
                </span>
                <button
                  onClick={handleCopyKey}
                  className="flex items-center gap-1 text-[11px] text-stellar-cyan hover:text-white transition-colors"
                >
                  {copiedKey ? <Check className="w-3 h-3 text-stellar-emerald" /> : <Copy className="w-3 h-3" />}
                  {copiedKey ? 'Copied' : 'Copy PEM'}
                </button>
              </div>
              <pre className="text-[10px] text-slate-300 overflow-x-auto p-2 bg-space-900/90 rounded border border-space-850 font-mono-tech max-h-24">
                {node.public_key || 'No public key registered'}
              </pre>
            </div>

            {/* Security Guarantee Banner */}
            <div className="p-2.5 rounded bg-stellar-emerald/5 border border-stellar-emerald/20 flex items-center gap-2 text-[11px] text-slate-400">
              <ShieldCheck className="w-4 h-4 text-stellar-emerald shrink-0" />
              <span>Cryptographic Security Invariant: Private keys reside exclusively within the local node wallet.</span>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
