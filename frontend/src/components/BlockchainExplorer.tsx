import React, { useState } from 'react';
import { 
  Blocks, 
  ChevronLeft, 
  ChevronRight, 
  Clock, 
  FileText, 
  Hash, 
  User, 
  ShieldCheck, 
  Eye, 
  X,
  Cpu
} from 'lucide-react';
import { BlockSummary, BlockDetail } from '../types/api';
import { apiService } from '../services/api';

interface BlockchainExplorerProps {
  blocks: BlockSummary[];
  totalBlocks: number;
  currentPage: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  isLoading?: boolean;
}

export const BlockchainExplorer: React.FC<BlockchainExplorerProps> = ({
  blocks,
  totalBlocks,
  currentPage,
  pageSize,
  onPageChange,
  isLoading = false,
}) => {
  const [selectedBlockHeight, setSelectedBlockHeight] = useState<number | null>(null);
  const [blockDetail, setBlockDetail] = useState<BlockDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const totalPages = Math.max(1, Math.ceil(totalBlocks / pageSize));

  const handleInspectBlock = (height: number) => {
    setSelectedBlockHeight(height);
    setLoadingDetail(true);
    apiService.getBlock(height)
      .then((data) => setBlockDetail(data))
      .catch((err) => console.error('Failed to load block detail:', err))
      .finally(() => setLoadingDetail(false));
  };

  const closeDetail = () => {
    setSelectedBlockHeight(null);
    setBlockDetail(null);
  };

  const formatHash = (h?: string | null) => {
    if (!h) return 'N/A';
    if (h.length <= 20) return h;
    return `${h.slice(0, 10)}...${h.slice(-10)}`;
  };

  const formatTimestamp = (ts: any) => {
    if (!ts) return 'N/A';
    try {
      const d = typeof ts === 'number' ? new Date(ts > 1e11 ? ts : ts * 1000) : new Date(ts);
      return d.toLocaleString();
    } catch {
      return String(ts);
    }
  };

  return (
    <div className="panel" style={{ padding: '16px 20px' }}>
      <div className="section-header">
        <div className="section-title">
          <Blocks size={14} style={{ color: 'var(--accent)' }} />
          Blockchain Ledger
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
          Total: <strong style={{ color: 'var(--text)' }}>{totalBlocks}</strong> blocks
        </span>
      </div>

      {blocks.length === 0 ? (
        <div style={{ padding: '40px 0', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
          No blocks recorded in canonical chain.
        </div>
      ) : (
        <div style={{ overflowX: 'auto', margin: '12px 0' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Height</th>
                <th>Block Hash</th>
                <th>Previous Hash</th>
                <th>Proposer</th>
                <th>TXs</th>
                <th>Timestamp</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {blocks.map((b) => (
                <tr
                  key={`block-${b.height}-${b.hash}`}
                  onClick={() => handleInspectBlock(b.height)}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ color: 'var(--accent)', fontWeight: 700 }}>#{b.height}</td>
                  <td style={{ color: 'var(--text)' }} title={b.hash}>{formatHash(b.hash)}</td>
                  <td style={{ color: 'var(--text-muted)' }} title={b.previous_hash || ''}>{formatHash(b.previous_hash)}</td>
                  <td style={{ color: 'var(--text-muted)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={b.creator}>
                    {b.creator.includes('BEGIN') ? 'Validator' : b.creator}
                  </td>
                  <td style={{ color: 'var(--text)', fontWeight: 600 }}>{b.transaction_count}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{formatTimestamp(b.timestamp)}</td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleInspectBlock(b.height); }}
                      className="btn btn--ghost"
                      style={{ padding: '3px 8px', fontSize: '0.6875rem', display: 'inline-flex', alignItems: 'center', gap: 4 }}
                    >
                      <Eye size={11} />Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 12, borderTop: '1px solid var(--border-subtle)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
        <span style={{ color: 'var(--text-dim)' }}>Page {currentPage + 1} / {totalPages}</span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={() => onPageChange(Math.max(0, currentPage - 1))}
            disabled={currentPage === 0 || isLoading}
            className="btn btn--ghost"
            style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: 4 }}
          >
            <ChevronLeft size={13} /> Prev
          </button>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage + 1 >= totalPages || isLoading}
            className="btn btn--ghost"
            style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: 4 }}
          >
            Next <ChevronRight size={13} />
          </button>
        </div>
      </div>

      {/* Block Detail Modal */}
      {selectedBlockHeight !== null && (
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, background: 'rgba(0,0,0,0.8)' }}
          onClick={closeDetail}
        >
          <div
            className="panel"
            style={{ width: '100%', maxWidth: 600, maxHeight: '85vh', overflowY: 'auto', padding: 24, position: 'relative', background: 'var(--surface)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <button onClick={closeDetail} className="btn btn--icon" style={{ position: 'absolute', top: 16, right: 16 }}>
              <X size={15} />
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingBottom: 14, borderBottom: '1px solid var(--border-subtle)', marginBottom: 16 }}>
              <div style={{ width: 36, height: 36, background: 'var(--surface-inset)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Blocks size={18} style={{ color: 'var(--accent)' }} />
              </div>
              <div>
                <h3 style={{ fontFamily: 'var(--font-ui)', fontSize: '0.9375rem', fontWeight: 700, color: 'var(--text)', lineHeight: 1.2 }}>
                  Block #{selectedBlockHeight}
                </h3>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: 2 }}>
                  {blockDetail?.consensus_type.toUpperCase()}
                </p>
              </div>
            </div>

            {loadingDetail ? (
              <div style={{ padding: '40px 0', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Loading block data…
              </div>
            ) : blockDetail ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14, fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                <div className="panel--inset" style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div>
                    <span className="label">Block hash</span>
                    <span style={{ display: 'block', color: 'var(--accent)', wordBreak: 'break-all', marginTop: 3 }}>{blockDetail.hash}</span>
                  </div>
                  <div>
                    <span className="label">Previous hash</span>
                    <span style={{ display: 'block', color: 'var(--text-muted)', wordBreak: 'break-all', marginTop: 3 }}>{blockDetail.previous_hash || 'Genesis'}</span>
                  </div>
                  <div>
                    <span className="label">Proposer</span>
                    <span style={{ display: 'block', color: 'var(--text)', wordBreak: 'break-all', marginTop: 3 }}>{blockDetail.creator}</span>
                  </div>
                </div>

                {blockDetail.pos_metadata && (
                  <div className="panel--inset" style={{ padding: '10px 12px' }}>
                    <div className="label" style={{ display: 'block', marginBottom: 8 }}>
                      <Cpu size={11} style={{ display: 'inline', marginRight: 4 }} />
                      PoS VRF Snapshot
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                      <div>
                        <span className="label">Epoch seed</span>
                        <span style={{ display: 'block', color: 'var(--text-muted)', marginTop: 2, wordBreak: 'break-all' }}>{blockDetail.pos_metadata.seed || '—'}</span>
                      </div>
                      <div>
                        <span className="label">Creator stake</span>
                        <span style={{ display: 'block', color: 'var(--accent)', marginTop: 2 }}>{blockDetail.pos_metadata.staked_amt} ⬡</span>
                      </div>
                    </div>
                  </div>
                )}

                <div>
                  <div className="label" style={{ display: 'block', marginBottom: 8 }}>
                    <FileText size={11} style={{ display: 'inline', marginRight: 4 }} />
                    Transactions ({blockDetail.transactions.length})
                  </div>
                  {blockDetail.transactions.length === 0 ? (
                    <div style={{ padding: 12, textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.6875rem' }}>No transactions.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 200, overflowY: 'auto' }}>
                      {blockDetail.transactions.map((tx, idx) => (
                        <div key={`tx-${tx.id || idx}`} className="panel--inset" style={{ padding: '8px 10px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                            <span style={{ color: 'var(--accent)' }}>ID: {tx.id.slice(0, 14)}…</span>
                            <span style={{ color: 'var(--ok)', fontWeight: 700 }}>{JSON.stringify(tx.payload)} ⬡</span>
                          </div>
                          <div style={{ color: 'var(--text-dim)', fontSize: '0.6875rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {tx.sender.slice(0, 20)}… → {tx.receiver.slice(0, 20)}…
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};
