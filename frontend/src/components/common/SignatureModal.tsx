/**
 * Electronic Signature Modal
 * Implements 21 CFR Part 11 §11.200 re-authentication requirement.
 * User must re-enter their password (not just use existing JWT session)
 * to create a legally binding electronic signature.
 */
import React, { useState } from 'react';

interface Props {
  isOpen: boolean;
  meaning: string;
  username: string;
  onConfirm: (password: string, comment?: string) => Promise<void>;
  onCancel: () => void;
  requireComment?: boolean;
  title?: string;
}

export const SignatureModal: React.FC<Props> = ({
  isOpen,
  meaning,
  username,
  onConfirm,
  onCancel,
  requireComment = false,
  title = 'Electronic Signature Required',
}) => {
  const [password, setPassword] = useState('');
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) {
      setError('Password is required');
      return;
    }
    if (requireComment && comment.length < 10) {
      setError('Comment must be at least 10 characters');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await onConfirm(password, comment);
      setPassword('');
      setComment('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Signature failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <h3 style={{ marginTop: 0, color: '#1e40af' }}>{title}</h3>

        <div style={{ background: '#f0f9ff', border: '1px solid #93c5fd', padding: 12, borderRadius: 4, marginBottom: 16 }}>
          <strong>Meaning of this signature:</strong>
          <p style={{ margin: '8px 0 0', fontStyle: 'italic' }}>{meaning}</p>
        </div>

        <p style={{ fontSize: 13, color: '#6b7280' }}>
          Signing as: <strong>{username}</strong> | Per 21 CFR Part 11 §11.200
        </p>

        <form onSubmit={handleSubmit}>
          {requireComment && (
            <div style={{ marginBottom: 12 }}>
              <label style={labelStyle}>Comment (required)</label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={3}
                style={inputStyle}
                placeholder="Minimum 10 characters..."
                required
              />
            </div>
          )}

          <div style={{ marginBottom: 12 }}>
            <label style={labelStyle}>Password (re-authentication required)</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={inputStyle}
              autoFocus
              required
            />
          </div>

          {error && (
            <div style={{ color: '#ef4444', marginBottom: 8, fontSize: 13 }}>{error}</div>
          )}

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" onClick={onCancel} style={cancelBtnStyle} disabled={loading}>
              Cancel
            </button>
            <button type="submit" style={confirmBtnStyle} disabled={loading}>
              {loading ? 'Signing...' : 'Sign & Confirm'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const overlayStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
};
const modalStyle: React.CSSProperties = {
  background: '#fff', padding: 24, borderRadius: 8, maxWidth: 480, width: '100%',
  boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
};
const labelStyle: React.CSSProperties = { display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 600 };
const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 10px', border: '1px solid #d1d5db',
  borderRadius: 4, fontSize: 14, boxSizing: 'border-box',
};
const cancelBtnStyle: React.CSSProperties = {
  padding: '8px 16px', border: '1px solid #d1d5db', borderRadius: 4,
  background: '#fff', cursor: 'pointer',
};
const confirmBtnStyle: React.CSSProperties = {
  padding: '8px 16px', border: 'none', borderRadius: 4,
  background: '#1e40af', color: '#fff', cursor: 'pointer', fontWeight: 600,
};
