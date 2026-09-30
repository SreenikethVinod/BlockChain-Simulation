import React from 'react';
import { Inbox, Clock } from 'lucide-react';
import { MempoolResponse } from '../types/api';

interface MempoolViewerProps {
  mempool: MempoolResponse | null;
}

const abbr = (addr?: string) => {
  if (!addr) return '—';
  if (addr.includes('BEGIN')) return 'PK:…';
  if (addr.length <= 16) return addr;
  return `${addr.slice(0, 8)}…${addr.slice(-6)}`;
};

const fmt = (ts: any) => {
  if (!ts) return '—';
  try {
    const d = typeof ts === 'number' ? new Date(ts > 1e11 ? ts : ts * 1000) : new Date(ts);
    return d.toLocaleTimeString();
  } catch { return String(ts); }
};

export const MempoolViewer: React.FC<MempoolViewerProps> = ({ mempool }) => {
  const transactions = mempool?.transactions || [];

  return (
    <div className="panel" style={{ padding: '16px 20px' }}>
      <div className="section-header">
        <div className="section-title">
          <Inbox size={14} style={{ color: 'var(--warn)' }} />
          Mempool
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
          Pending: <strong style={{ color: 'var(--warn)' }}>{transactions.length}</strong>
        </span>
      </div>

      {transactions.length === 0 ? (
        <div
          data-testid="mempool-empty-state"
          style={{ padding: '28px 0', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-dim)' }}
        >
          Queue empty.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>TX ID</th>
                <th>From</th>
                <th>To</th>
                <th>Amount</th>
                <th style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Clock size={10} /> Time</th>
                <th style={{ textAlign: 'right' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id}>
                  <td style={{ color: 'var(--accent)' }}>{tx.id.slice(0, 14)}…</td>
                  <td style={{ color: 'var(--text-muted)' }} title={tx.sender}>{abbr(tx.sender)}</td>
                  <td style={{ color: 'var(--text-muted)' }} title={tx.receiver}>{abbr(tx.receiver)}</td>
                  <td style={{ color: 'var(--text)', fontWeight: 700 }}>{JSON.stringify(tx.payload)} ⬡</td>
                  <td style={{ color: 'var(--text-dim)' }}>{fmt(tx.timestamp)}</td>
                  <td style={{ textAlign: 'right' }}>
                    <span className="status-badge status-badge--warn">Pending</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
