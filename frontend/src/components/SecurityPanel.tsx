import React from 'react';
import { Shield, GitFork, Slash, AlertTriangle, Lock, CheckCircle } from 'lucide-react';
import { AttackTelemetryResponse } from '../types/api';

interface SecurityPanelProps {
  attacks: AttackTelemetryResponse | null;
}

export const SecurityPanel: React.FC<SecurityPanelProps> = ({ attacks }) => {
  const forks       = attacks?.forks_detected ?? 0;
  const slashes     = attacks?.slashing_incidents ?? 0;
  const doubleSigns = attacks?.double_sign_attempts ?? 0;
  const invalidBlks = attacks?.invalid_blocks_rejected ?? 0;
  const incidents   = attacks?.incidents || [];

  const fmt = (ts: number) => {
    try { return new Date(ts > 1e11 ? ts : ts * 1000).toLocaleTimeString(); }
    catch { return String(ts); }
  };

  const counts = [
    { label: 'Forks detected',        val: forks,       icon: <GitFork size={13} />,      alert: forks > 0 },
    { label: 'Slashing incidents',     val: slashes,     icon: <Slash size={13} />,        alert: slashes > 0 },
    { label: 'Double-sign attempts',   val: doubleSigns, icon: <AlertTriangle size={13} />, alert: doubleSigns > 0 },
    { label: 'Invalid blocks rejected',val: invalidBlks, icon: <Lock size={13} />,         alert: false },
  ];

  return (
    <div className="panel" style={{ padding: '16px 20px' }}>
      {/* Header */}
      <div className="section-header">
        <div className="section-title">
          <Shield size={14} style={{ color: 'var(--fail)' }} />
          Security Telemetry
        </div>
        <span className="status-badge status-badge--live">Monitoring</span>
      </div>

      {/* Counter row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 8,
          marginBottom: 18,
        }}
        className="sec-grid"
      >
        <style>{`@media (max-width: 640px) { .sec-grid { grid-template-columns: repeat(2, 1fr) !important; } }`}</style>
        {counts.map(({ label, val, icon, alert }) => (
          <div
            key={label}
            style={{
              background: 'var(--surface-inset)',
              border: `1px solid ${alert ? 'var(--danger-dim)' : 'var(--border-subtle)'}`,
              borderRadius: 'var(--radius-sm)',
              padding: '10px 12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span className="label">{label}</span>
              <span style={{ color: alert ? 'var(--fail)' : 'var(--text-dim)' }}>{icon}</span>
            </div>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '1.25rem',
                fontWeight: 700,
                color: alert ? 'var(--fail)' : 'var(--text-muted)',
              }}
            >
              {val}
            </span>
          </div>
        ))}
      </div>

      {/* Incident log */}
      <div>
        <h3
          style={{
            fontFamily: 'var(--font-ui)',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: 'var(--text-muted)',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            marginBottom: 10,
          }}
        >
          Incident Log ({incidents.length})
        </h3>

        {incidents.length === 0 ? (
          <div
            data-testid="security-empty-state"
            style={{
              padding: '28px 0',
              textAlign: 'center',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: 'var(--text-dim)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <CheckCircle size={20} style={{ color: 'var(--ok)', opacity: 0.5 }} />
            All consensus rules nominal. No incidents recorded.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 240, overflowY: 'auto' }}>
            {incidents.map((inc: any, i: number) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  padding: '8px 10px',
                  background: 'var(--surface-inset)',
                  borderLeft: '3px solid var(--fail)',
                  borderRadius: 'var(--radius-sm)',
                  gap: 10,
                }}
              >
                <div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', fontWeight: 700, color: 'var(--fail)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                    {inc.type?.replace('_', ' ')}
                  </span>
                  <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', margin: '3px 0 0' }}>
                    {inc.reason || JSON.stringify(inc)}
                  </p>
                  {inc.validator && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-dim)', display: 'block', marginTop: 2 }}>
                      {inc.validator.slice(0, 40)}…
                    </span>
                  )}
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-dim)', flexShrink: 0 }}>
                  {inc.time ? fmt(inc.time) : '—'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
