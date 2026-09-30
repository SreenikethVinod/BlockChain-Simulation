import React from 'react';
import { RefreshCw, Cpu } from 'lucide-react';
import { NetworkResponse, WebSocketStatus } from '../types/api';

interface HeaderProps {
  network: NetworkResponse | null;
  wsStatus: WebSocketStatus;
  isBackendOnline: boolean;
  onRefresh: () => void;
  isRefreshing: boolean;
  telemetryPhrase?: string;
}

export const Header: React.FC<HeaderProps> = ({
  network,
  wsStatus,
  isBackendOnline,
  onRefresh,
  isRefreshing,
  telemetryPhrase = 'Mission Control Status: Stellar',
}) => {
  const isStandalone = network?.is_standalone || network?.simulation_mode === 'standalone';
  const roomId = network?.room_id || 'LOCAL';

  const wsLabel =
    wsStatus === 'connected'    ? 'WS LIVE'       :
    wsStatus === 'reconnecting' ? 'WS RECONNECT'  : 'WS OFFLINE';
  const wsClass =
    wsStatus === 'connected'    ? 'status-badge--live'   :
    wsStatus === 'reconnecting' ? 'status-badge--warn'   : 'status-badge--offline';

  const connLabel =
    !isBackendOnline ? 'OFFLINE'    :
    isStandalone     ? 'STANDALONE' : 'LIVE';
  const connClass =
    !isBackendOnline ? 'status-badge--danger' :
    isStandalone     ? 'status-badge--warn'   : 'status-badge--live';

  return (
    <header
      style={{
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
      }}
      className="sticky top-0 z-40 px-5 py-3"
    >
      <div className="flex items-center justify-between gap-4">
        {/* Left — identity */}
        <div className="flex items-center gap-3 min-w-0">
          <div
            style={{ border: '1px solid var(--border-strong)', borderRadius: '4px', padding: '6px' }}
          >
            <Cpu style={{ width: 16, height: 16, color: 'var(--accent)' }} />
          </div>
          <div className="min-w-0">
            <h1
              style={{
                fontFamily: 'var(--font-ui)',
                fontSize: '0.9375rem',
                fontWeight: 700,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: 'var(--text)',
                lineHeight: 1.2,
              }}
            >
              Blockchain Mission Control
            </h1>
            <p
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.6875rem',
                color: 'var(--text-muted)',
                letterSpacing: '0.03em',
                lineHeight: 1.4,
              }}
            >
              {telemetryPhrase}
            </p>
          </div>
        </div>

        {/* Right — status indicators */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Connection mode */}
          <span
            data-testid={isBackendOnline ? (isStandalone ? 'mode-standalone' : 'mode-live') : 'mode-offline'}
            className={`status-badge ${connClass}`}
          >
            <span className={`status-dot status-dot--${!isBackendOnline ? 'offline' : isStandalone ? 'warn' : 'live'}`} />
            {connLabel}
          </span>

          {/* Room ID */}
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.6875rem',
              color: 'var(--text-muted)',
              padding: '3px 8px',
              background: 'var(--surface-inset)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            {roomId}
          </span>

          {/* WebSocket */}
          <span
            data-testid="ws-status"
            className={`status-badge ${wsClass}`}
          >
            <span
              className={wsStatus === 'connected' ? 'status-dot status-dot--live animate-live' :
                         wsStatus === 'reconnecting' ? 'status-dot status-dot--warn animate-live' :
                         'status-dot status-dot--offline'}
            />
            {wsLabel}
          </span>

          {/* Refresh */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="btn btn--icon"
            title="Refresh telemetry"
          >
            <RefreshCw
              style={{ width: 14, height: 14 }}
              className={isRefreshing ? 'animate-spin' : ''}
            />
          </button>
        </div>
      </div>
    </header>
  );
};
