/**
 * Calibration page — manage calibration records for detectors.
 * Creating calibration records requires electronic signature (EMISSIONS/OPERATOR/ADMIN).
 * Records are immutable once created.
 */
import React, { useEffect, useState } from 'react';
import { SignatureModal } from '../components/common/SignatureModal';
import { useAuthStore } from '../store/authStore';
import api from '../services/api';
import { format } from 'date-fns';

interface CalibrationRecord {
  calibration_id: number;
  channel_id: number;
  channel_code: string;
  calibration_date: string;
  next_calibration_due: string;
  calibration_factor: number;
  reference_standard: string;
  performed_by_username: string;
  approved_by_username: string | null;
  notes: string | null;
  is_current: boolean;
}

interface Channel {
  channel_id: number;
  channel_code: string;
  channel_name: string;
}

export const Calibration: React.FC = () => {
  const { user } = useAuthStore();
  const [records, setRecords] = useState<CalibrationRecord[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [showSignModal, setShowSignModal] = useState(false);
  const [formData, setFormData] = useState({
    channel_id: '',
    calibration_date: new Date().toISOString().split('T')[0],
    next_calibration_due: '',
    calibration_factor: '1.0',
    reference_standard: '',
    notes: '',
  });
  const [pendingForm, setPendingForm] = useState<typeof formData | null>(null);

  const fetchRecords = async () => {
    const resp = await api.get<CalibrationRecord[]>('/calibration?limit=100');
    setRecords(resp.data);
  };

  useEffect(() => {
    fetchRecords();
    api.get<Channel[]>('/channels').then(r => setChannels(r.data));
    // Default next cal due: 1 year from today
    const nextYear = new Date();
    nextYear.setFullYear(nextYear.getFullYear() + 1);
    setFormData(f => ({ ...f, next_calibration_due: nextYear.toISOString().split('T')[0] }));
  }, []);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPendingForm({ ...formData });
    setShowForm(false);
    setShowSignModal(true);
  };

  const handleSignConfirm = async (password: string, comment?: string) => {
    if (!pendingForm) return;
    await api.post('/calibration', {
      ...pendingForm,
      channel_id: Number(pendingForm.channel_id),
      calibration_factor: parseFloat(pendingForm.calibration_factor),
      signature_password: password,
      meaning: `I certify this calibration record for channel ${channels.find(c => c.channel_id === Number(pendingForm.channel_id))?.channel_code} is accurate and traceable to reference standards.`,
    });
    setShowSignModal(false);
    setPendingForm(null);
    await fetchRecords();
  };

  const daysUntilDue = (due: string) => {
    const d = Math.ceil((new Date(due).getTime() - Date.now()) / (1000 * 86400));
    return d;
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 20, color: '#1e293b' }}>Calibration Records</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{ padding: '8px 16px', background: '#1e40af', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}
        >
          + New Calibration
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleFormSubmit} style={{
          background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0',
          padding: 20, marginBottom: 20,
        }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 14 }}>New Calibration Record</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { label: 'Channel', key: 'channel_id', type: 'select' },
              { label: 'Calibration Date', key: 'calibration_date', type: 'date' },
              { label: 'Next Due Date', key: 'next_calibration_due', type: 'date' },
              { label: 'Calibration Factor', key: 'calibration_factor', type: 'number' },
              { label: 'Reference Standard', key: 'reference_standard', type: 'text' },
            ].map(field => (
              <div key={field.key}>
                <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>{field.label}</label>
                {field.type === 'select' ? (
                  <select value={(formData as any)[field.key]}
                    onChange={e => setFormData(f => ({ ...f, [field.key]: e.target.value }))}
                    required
                    style={{ width: '100%', padding: '7px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 }}>
                    <option value="">Select…</option>
                    {channels.map(c => <option key={c.channel_id} value={c.channel_id}>{c.channel_code} — {c.channel_name}</option>)}
                  </select>
                ) : (
                  <input type={field.type} value={(formData as any)[field.key]}
                    onChange={e => setFormData(f => ({ ...f, [field.key]: e.target.value }))}
                    required
                    style={{ width: '100%', padding: '7px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 }} />
                )}
              </div>
            ))}
            <div>
              <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>Notes</label>
              <textarea value={formData.notes} onChange={e => setFormData(f => ({ ...f, notes: e.target.value }))}
                rows={2}
                style={{ width: '100%', padding: '7px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13, resize: 'vertical' }} />
            </div>
          </div>
          <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
            <button type="submit"
              style={{ padding: '8px 18px', background: '#1e40af', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
              Submit (requires signature)
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              style={{ padding: '8px 14px', background: '#e2e8f0', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
              {['Channel', 'Cal. Date', 'Next Due', 'Status', 'Factor', 'Reference', 'Performed By', 'Current'].map(h => (
                <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', fontSize: 12 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {records.length === 0 && (
              <tr><td colSpan={8} style={{ padding: 20, textAlign: 'center', color: '#9ca3af' }}>No calibration records</td></tr>
            )}
            {records.map(r => {
              const days = daysUntilDue(r.next_calibration_due);
              const statusColor = days < 0 ? '#dc2626' : days < 30 ? '#d97706' : '#16a34a';
              const statusText = days < 0 ? `OVERDUE ${Math.abs(days)}d` : days < 30 ? `DUE IN ${days}d` : `OK ${days}d`;
              return (
                <tr key={r.calibration_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '9px 12px', fontWeight: 600 }}>{r.channel_code}</td>
                  <td style={{ padding: '9px 12px', fontSize: 12 }}>{format(new Date(r.calibration_date), 'yyyy-MM-dd')}</td>
                  <td style={{ padding: '9px 12px', fontSize: 12 }}>{format(new Date(r.next_calibration_due), 'yyyy-MM-dd')}</td>
                  <td style={{ padding: '9px 12px' }}>
                    <span style={{ color: statusColor, fontWeight: 600, fontSize: 11 }}>{statusText}</span>
                  </td>
                  <td style={{ padding: '9px 12px', fontFamily: 'monospace' }}>{r.calibration_factor}</td>
                  <td style={{ padding: '9px 12px', color: '#64748b' }}>{r.reference_standard}</td>
                  <td style={{ padding: '9px 12px', color: '#64748b' }}>{r.performed_by_username}</td>
                  <td style={{ padding: '9px 12px' }}>
                    {r.is_current && <span style={{ color: '#16a34a', fontWeight: 600, fontSize: 11 }}>CURRENT</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showSignModal && (
        <SignatureModal
          isOpen={true}
          title="Sign Calibration Record"
          meaning={`I certify this calibration record is accurate and traceable to reference standards.`}
          username={user?.username || ''}
          onConfirm={handleSignConfirm}
          onCancel={() => { setShowSignModal(false); setPendingForm(null); }}
          requireComment={false}
        />
      )}
    </div>
  );
};
