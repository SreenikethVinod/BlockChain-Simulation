import React from 'react';
import { Terminal, Trash2 } from 'lucide-react';
import { WebSocketEvent } from '../types/api';

interface EventConsoleProps {
  events: WebSocketEvent[];
  onClear: () => void;
}

const EVENT_COLORS: Record<string, { color: string; label: string }> = {
  block_created:      { color: 'var(--info)',    label: 'BLOCK' },
  block_received:     { color: 'var(--info)',    label: 'BLOCK' },
  transaction_received: { color: 'var(--ok)',   label: 'TX' },
  validator_selected: { color: 'var(--accent)', label: 'VALIDATOR' },
  stake_added:        { color: 'var(--accent)', label: 'STAKE' },
  fork_detected:      { color: 'var(--fail)',   label: 'FORK' },
  validator_slashed:  { color: 'var(--fail)',   label: 'SLASHED' },
  peer_joined:        { color: 'var(--ok)',     label: 'PEER+' },
  peer_left:          { color: 'var(--text-muted)', label: 'PEER-' },
};

export const EventConsole: React.FC<EventConsoleProps> = ({ events, onClear }) => {
  const [filter, setFilter] = React.useState('all');

  const filtered = events.filter((e) => {
    if (filter === 'all') return true;
    if (filter === 'blocks') return e.event.includes('block');
    if (filter === 'tx') return e.event.includes('transaction');
    if (filter === 'consensus') return e.event.includes('validator') || e.event.includes('stake');
    if (filter === 'security') return e.event.includes('fork') || e.event.includes('slashed');
    if (filter === 'network') return e.event.includes('peer');
    return true;
  });

  const fmt = (ts: number) => {
    try {
      const d = new Date(ts > 1e11 ? ts : ts * 1000);
      return `${d.toLocaleTimeString()}.${String(d.getMilliseconds()).padStart(3, '0')}`;
    } catch { return String(ts); }
  };

  return (
    <div className="panel" style={{ padding: '14px 18px' }}>
      <div className="section-header">
        <div className="section-title">
          <Terminal size={14} style={{ color: 'var(--accent)' }} />
          Event Stream
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.6875rem',
              color: 'var(--text-dim)',
              padding: '1px 6px',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            {events.length}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="ctrl-select"
          >
            <option value="all">All</option>
            <option value="blocks">Blocks</option>
            <option value="tx">Transactions</option>
            <option value="consensus">Consensus</option>
            <option value="security">Security</option>
            <option value="network">Network</option>
          </select>
          <button onClick={onClear} className="btn btn--icon" title="Clear log">
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div
          data-testid="events-empty-state"
          style={{ padding: '28px 0', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-dim)' }}
        >
          No events. Listening for WebSocket dispatches…
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, maxHeight: 300, overflowY: 'auto' }}>
          {filtered.map((evt, idx) => {
            const meta = EVENT_COLORS[evt.event] || { color: 'var(--text-muted)', label: evt.event.toUpperCase() };
            return (
              <div
                key={`${idx}-${evt.timestamp}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '5px 8px',
                  borderRadius: 'var(--radius-sm)',
                  background: idx % 2 === 0 ? 'transparent' : 'var(--surface-inset)',
                  gap: 10,
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.6875rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                  <span
                    style={{
                      color: meta.color,
                      fontWeight: 700,
                      letterSpacing: '0.05em',
                      width: 80,
                      flexShrink: 0,
                    }}
                  >
                    {meta.label}
                  </span>
                  <span style={{ color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {JSON.stringify(evt.data)}
                  </span>
                </div>
                <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>
                  {fmt(evt.timestamp)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
