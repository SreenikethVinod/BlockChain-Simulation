import React, { useState, useCallback, memo } from 'react';
import { NetworkResponse } from '../types/api';

interface NetworkTopologyProps {
  network: NetworkResponse | null;
  onSelectNode: (nodeId: string) => void;
  selectedNodeId?: string | null;
}

/**
 * NetworkTopology — P2P Mesh visualization.
 *
 * Graph fix preserved:
 * - SVG hover uses onMouseEnter/Leave + radius expansion, NOT CSS hover:scale-105.
 *   (CSS scale on SVG <g> uses transform-origin (0,0) of the SVG viewport, causing jump.)
 * - React.memo prevents re-renders from parent polling causing node recalculation mid-hover.
 */
export const NetworkTopology: React.FC<NetworkTopologyProps> = memo(function NetworkTopology({
  network,
  onSelectNode,
  selectedNodeId,
}) {
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const handleMouseEnter = useCallback((id: string) => setHoveredNodeId(id), []);
  const handleMouseLeave = useCallback(() => setHoveredNodeId(null), []);

  const nodes = network?.nodes || [];
  const roomId = network?.room_id || 'LOCAL';

  if (!network || nodes.length === 0) {
    return (
      <div
        className="panel"
        style={{ padding: '48px 24px', textAlign: 'center' }}
      >
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-dim)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8 }}>
          No Active Network
        </div>
        <div style={{ fontFamily: 'var(--font-ui)', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          Start a blockchain node and join a room to begin peer discovery.
        </div>
      </div>
    );
  }

  const W = 600;
  const H = 340;
  const centerX = W / 2;
  const centerY = H / 2 + 10;
  const radius = nodes.length > 1 ? 120 : 0;

  const nodePositions = nodes.map((n, i) => {
    if (nodes.length === 1) return { ...n, x: centerX, y: centerY };
    const angle = (i * 2 * Math.PI) / nodes.length - Math.PI / 2;
    return { ...n, x: centerX + radius * Math.cos(angle), y: centerY + radius * Math.sin(angle) };
  });

  // Design tokens for SVG (must use literal values — SVG doesn't inherit CSS variables)
  const COL = {
    bg:         '#0b0d0f',
    grid:       'rgba(255,255,255,0.025)',
    ring:       '#272c31',
    p2pLink:    '#2a3a2e',
    p2pDot:     '#3a8c5e',
    sigLink:    '#272c31',
    nodeBase:   '#16191c',
    nodeBorder: '#272c31',
    nodeActive: '#d4891a',  // accent — amber
    nodeOk:     '#3a8c5e',
    nodeText:   '#dde2e8',
    nodeMuted:  '#6e7a86',
    hoverRing:  '#363d44',
    sigStation: '#1d2126',
    sigBorder:  '#363d44',
    sigText:    '#6e7a86',
    sigLabel:   '#d4891a',
  };

  return (
    <div className="panel" style={{ padding: '16px 18px' }}>
      {/* Header */}
      <div className="section-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <h2 className="section-title">P2P Mesh Topology</h2>
          <span className="status-badge status-badge--neutral" style={{ fontFamily: 'var(--font-mono)' }}>
            {nodes.length} {nodes.length === 1 ? 'node' : 'nodes'}
          </span>
          <span className="status-badge status-badge--neutral" style={{ fontFamily: 'var(--font-mono)' }}>
            {roomId}
          </span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-dim)' }}>
          Hover · click to inspect
        </span>
      </div>

      {/* SVG Canvas */}
      <div
        style={{
          width: '100%',
          background: COL.bg,
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          overflow: 'hidden',
          marginBottom: 12,
        }}
      >
        <svg
          viewBox={`0 0 ${W} ${H}`}
          style={{ display: 'block', width: '100%', minHeight: 260 }}
          aria-label="P2P network topology diagram"
        >
          <defs>
            <pattern id="eng-grid" width="24" height="24" patternUnits="userSpaceOnUse">
              <path d="M 24 0 L 0 0 0 24" fill="none" stroke={COL.grid} strokeWidth="0.5" />
            </pattern>
          </defs>

          {/* Background grid */}
          <rect width={W} height={H} fill={`url(#eng-grid)`} />

          {/* Orbital guide ring */}
          {nodes.length > 1 && (
            <circle
              cx={centerX} cy={centerY} r={radius}
              fill="none"
              stroke={COL.ring}
              strokeWidth="1"
              strokeDasharray="4 6"
            />
          )}

          {/* Signalling station — clearly separated, labeled as discovery-only */}
          <g transform={`translate(${centerX}, 26)`}>
            <rect x="-68" y="-14" width="136" height="28" rx="2"
              fill={COL.sigStation} stroke={COL.sigBorder} strokeWidth="1" />
            <text x="0" y="-2" textAnchor="middle" fill={COL.sigLabel}
              fontSize="9" fontWeight="bold" fontFamily="monospace" letterSpacing="0.06em">
              SIGNALLING
            </text>
            <text x="0" y="10" textAnchor="middle" fill={COL.sigText}
              fontSize="7.5" fontFamily="monospace">
              Discovery only · no chain data
            </text>
            {/* Dotted lines to nodes */}
            {nodePositions.map((pos, idx) => (
              <line
                key={`sig-${idx}`}
                x1="0" y1="14"
                x2={pos.x - centerX} y2={pos.y - 26}
                stroke={COL.sigLink}
                strokeWidth="0.75"
                strokeDasharray="2 5"
              />
            ))}
          </g>

          {/* Direct P2P mesh links */}
          {nodePositions.map((a, i) =>
            nodePositions.slice(i + 1).map((b, j) => (
              <g key={`link-${i}-${j}`}>
                <line
                  x1={a.x} y1={a.y}
                  x2={b.x} y2={b.y}
                  stroke={COL.p2pLink}
                  strokeWidth="1.5"
                />
                {/* Center tick — subtle indicator of active link */}
                <circle
                  cx={(a.x + b.x) / 2}
                  cy={(a.y + b.y) / 2}
                  r="2.5"
                  fill={COL.p2pDot}
                />
              </g>
            ))
          )}

          {/* Node vessels */}
          {nodePositions.map((pos) => {
            const isSelected = selectedNodeId === pos.node_id;
            const isHovered = hoveredNodeId === pos.node_id;
            const isSelf = pos.is_self;

            // SVG-native radius expansion — no CSS scale transform.
            // CSS hover:scale on SVG <g> uses viewport (0,0) as transform-origin → node jumps.
            const outerR = isSelected ? 26 : isHovered ? 23 : 20;
            const borderColor = isSelected ? COL.nodeActive :
                                isHovered  ? (isSelf ? COL.nodeActive : COL.nodeOk) :
                                             COL.nodeBorder;
            const borderW = isSelected ? 2 : isHovered ? 1.5 : 1;

            return (
              <g
                key={pos.node_id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => onSelectNode(pos.node_id)}
                onMouseEnter={() => handleMouseEnter(pos.node_id)}
                onMouseLeave={handleMouseLeave}
                style={{ cursor: 'pointer' }}
                role="button"
                aria-label={`Node ${pos.name}`}
              >
                {/* Hover indicator ring — SVG-native, no CSS transform */}
                {isHovered && (
                  <circle cx="0" cy="0" r="30"
                    fill="none"
                    stroke={isSelf ? COL.nodeActive : COL.hoverRing}
                    strokeWidth="1"
                    strokeDasharray="3 4"
                    opacity="0.6"
                  />
                )}

                {/* Outer ring — radius changes in JS, not via CSS scale */}
                <circle cx="0" cy="0"
                  r={outerR}
                  fill={isSelf ? 'rgba(212,137,26,0.06)' : 'rgba(58,140,94,0.05)'}
                  stroke={borderColor}
                  strokeWidth={borderW}
                />

                {/* Inner solid node */}
                <circle cx="0" cy="0" r="13"
                  fill={COL.nodeBase}
                  stroke={isSelected ? COL.nodeActive : COL.ring}
                  strokeWidth="1"
                />

                {/* Node type label */}
                <text x="0" y="4" textAnchor="middle"
                  fill={isSelf ? COL.nodeActive : COL.nodeOk}
                  fontSize="8" fontWeight="bold" fontFamily="monospace"
                  letterSpacing="0.04em"
                >
                  {isSelf ? 'YOU' : 'P2P'}
                </text>

                {/* Name below */}
                <text x="0" y="33" textAnchor="middle"
                  fill={isHovered || isSelected ? COL.nodeText : '#b0b8c4'}
                  fontSize="10.5" fontWeight="600" fontFamily="sans-serif"
                >
                  {pos.name}
                </text>

                {/* Port · Consensus */}
                <text x="0" y="45" textAnchor="middle"
                  fill={COL.nodeMuted}
                  fontSize="8.5" fontFamily="monospace"
                >
                  :{pos.port} · {pos.consensus.toUpperCase()}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.6875rem',
          color: 'var(--text-dim)',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 16, height: 1, background: '#3a8c5e', display: 'inline-block' }} />
            Direct P2P link
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 16, height: 1, borderTop: '1px dashed #363d44', display: 'inline-block' }} />
            Signalling (discovery only)
          </span>
        </div>
        <span style={{ color: 'var(--accent)', opacity: 0.7 }}>
          {selectedNodeId ? `Selected: ${selectedNodeId}` : 'No node selected'}
        </span>
      </div>
    </div>
  );
});

NetworkTopology.displayName = 'NetworkTopology';
