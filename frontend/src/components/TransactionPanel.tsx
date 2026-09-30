import React, { useState } from 'react';
import { Send, CheckCircle2, AlertCircle, ShieldCheck, Loader2 } from 'lucide-react';
import { apiService } from '../services/api';
import { TransactionResponse } from '../types/api';

interface TransactionPanelProps {
  onTransactionSubmitted?: (tx: TransactionResponse) => void;
  availableBalance?: number | null;
}

export const TransactionPanel: React.FC<TransactionPanelProps> = ({
  onTransactionSubmitted,
  availableBalance,
}) => {
  const [receiver, setReceiver] = useState('');
  const [amount, setAmount] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successTx, setSuccessTx] = useState<TransactionResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessTx(null);
    const parsedAmount = parseFloat(amount);
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      setError('Amount must be a positive number.');
      return;
    }
    if (!receiver.trim()) {
      setError('Recipient must not be empty.');
      return;
    }
    setIsSubmitting(true);
    try {
      const resp = await apiService.submitTransaction({ receiver: receiver.trim(), amount: parsedAmount });
      setSuccessTx(resp);
      setAmount('');
      setReceiver('');
      onTransactionSubmitted?.(resp);
    } catch (err: any) {
      setError(err.message || 'Transaction rejected by node.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="panel" style={{ padding: '16px 20px' }}>
      <div className="section-header">
        <div className="section-title">
          <Send size={14} style={{ color: 'var(--ok)' }} />
          Send Transaction
        </div>
        {availableBalance != null && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Balance: <strong style={{ color: 'var(--accent)' }}>{availableBalance.toFixed(4)} ⬡</strong>
          </span>
        )}
      </div>

      <form onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div>
          <label className="label" style={{ display: 'block', marginBottom: 5 }}>
            Recipient (node name or public key)
          </label>
          <input
            type="text"
            data-testid="input-receiver"
            value={receiver}
            onChange={(e) => setReceiver(e.target.value)}
            placeholder="e.g. node2 or PEM public key"
            className="ctrl-input"
            disabled={isSubmitting}
          />
        </div>

        <div>
          <label className="label" style={{ display: 'block', marginBottom: 5 }}>
            Amount (⬡)
          </label>
          <input
            type="number"
            data-testid="input-amount"
            step="any"
            min="0.0001"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="e.g. 5.0"
            className="ctrl-input"
            disabled={isSubmitting}
          />
        </div>

        {error && (
          <div data-testid="tx-error-message" className="alert alert--error animate-fade-in">
            <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{error}</span>
          </div>
        )}

        {successTx && (
          <div data-testid="tx-success-message" className="alert alert--success animate-fade-in">
            <CheckCircle2 size={14} style={{ flexShrink: 0, marginTop: 1 }} />
            <div>
              <strong style={{ display: 'block', marginBottom: 2 }}>Transaction submitted</strong>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', opacity: 0.8 }}>
                {successTx.tx_id} · {successTx.amount} ⬡ → {successTx.receiver}
              </span>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 4 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-dim)' }}>
            <ShieldCheck size={12} style={{ color: 'var(--ok)' }} />
            ECDSA signed locally
          </span>
          <button
            type="submit"
            data-testid="submit-tx-btn"
            disabled={isSubmitting}
            className="btn btn--primary"
          >
            {isSubmitting ? (
              <><Loader2 size={13} className="animate-spin" /> Signing…</>
            ) : (
              <><Send size={13} /> Submit</>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
