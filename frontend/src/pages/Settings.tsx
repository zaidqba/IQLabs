/**
 * Settings page — threshold management with versioning and e-signature.
 * Threshold changes require electronic signature (OPERATOR/ADMIN).
 * Each change creates a new versioned alarm_profile row (immutable history).
 */
import React, { useEffect, useState } from 'react';
import { SignatureModal } from '../components/common/SignatureModal';
import { SEVERITY_COLORS } from '../types/common';
import { useAuthStore } from '../store/authStore';
import api from '../services/api';

interface Channel {
  channel_id: number;
  channel_code: string;
  channel_name: string;
  uom_symbol: string;
}

interface ThresholdProfile {
  profile_id: number;
  profile_version: number;
  low_threshold: number | null;
  alert_threshold: number | null;
  alarm_threshold: number | null;
  danger_threshold: number | null;
  high_dose_threshold: number | null;
  effective_from: string;
  is_current: boolean;
  changed_by_username: string | null;
  change_reason: string | null;
}

export const Settings: React.FC = () => {
  const { user } = useAuthStore();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<number | null>(null);
  const [profiles, setProfiles] = useState<ThresholdProfile[]>([]);
  const [editing, setEditing] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [changeReason, setChangeReason] = useState('');
  const [showSignModal, setShowSignModal] = useState(false);
  const [pendingPayload, setPendingPayload] = useState<any | null>(null);

  useEffect(() => {
    api.get<Channel[]>('/channels').then(r => {
      setChannels(r.data);
      if (r.data.length > 0) setSelectedChannel(r.data[0].channel_id);
    });
  }, []);

  useEffect(() => {
    if (!selectedChannel) return;
    api.get<ThresholdProfile[]>(`/channels/${selectedChannel}/thresholds/history`).then(r => {
      setProfiles(r.data);
      const current = r.data.find(p => p.is_current);
      if (current) {
        setEditValues({
          low_threshold: current.low_threshold?.toString() ?? '',
          alert_threshold: current.alert_threshold?.toString() ?? '',
          alarm_threshold: current.alarm_threshold?.toString() ?? '',
          danger_threshold: current.danger_threshold?.toString() ?? '',
          high_dose_threshold: current.high_dose_threshold?.toString() ?? '',
        });
      }
    });
  }, [selectedChannel]);

  const handleSaveClick = () => {
    if (!changeReason.trim()) { alert('Change reason is required'); return; }
    const payload: Record<string, number | null | string> = { change_reason: changeReason };
    for (const [k, v] of Object.entries(editValues)) {
      payload[k] = v === '' ? null : parseFloat(v);
    }
    setPendingPayload(payload);
    setShowSignModal(true);
  };

  const handleSignConfirm = async (password: string, _comment?: string) => {
    if (!pendingPayload || !selectedChannel) return;
    await api.patch(`/channels/${selectedChannel}/thresholds`, {
      ...pendingPayload,
      signature_password: password,
      meaning: `I approve the threshold change for channel ${channels.find(c => c.channel_id === selectedChannel)?.channel_code}. Reason: ${pendingPayload.change_reason}`,
    });
    setShowSignModal(false);
    setEditing(false);
    setPendingPayload(null);
    setChangeReason('');
    // Refresh
    const r = await api.get<ThresholdProfile[]>(`/channels/${selectedChannel}/thresholds/history`);
    setProfiles(r.data);
  };

  const ch = channels.find(c => c.channel_id === selectedChannel);
  const current = profiles.find(p => p.is_current);

  const thresholdFields = [
    { key: 'low_threshold', label: 'Low', color: SEVERITY_COLORS.LOW },
    { key: 'alert_threshold', label: 'Alert', color: SEVERITY_COLORS.ALERT },
    { key: 'alarm_threshold', label: 'Alarm', color: SEVERITY_COLORS.ALARM },
    { key: 'danger_threshold', label: 'Danger', color: SEVERITY_COLORS.DANGER },
    { key: 'high_dose_threshold', label: 'High Dose', color: SEVERITY_COLORS.HIGH_DOSE },
  ];

  return (
    <div>
      <h1 style={{ margin: '0 0 16px', fontSize: 20, color: '#1e293b' }}>Threshold Settings</h1>

      <div style={{
        background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6,
        padding: '8px 14px', marginBottom: 16, fontSize: 12, color: '#1e40af',
      }}>
        All threshold changes require electronic signature and are versioned — previous values are preserved in audit history.
      </div>

      <div style={{ display: 'flex', gap: 20 }}>
        {/* Channel list */}
        <div style={{ width: 220, flexShrink: 0 }}>
          <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
            {channels.map(c => (
              <button
                key={c.channel_id}
                onClick={() => { setSelectedChannel(c.channel_id); setEditing(false); }}
                style={{
                  width: '100%', padding: '10px 14px', border: 'none', textAlign: 'left',
                  background: selectedChannel === c.channel_id ? '#eff6ff' : '#fff',
                  borderLeft: selectedChannel === c.channel_id ? '3px solid #3b82f6' : '3px solid transparent',
                  cursor: 'pointer', fontSize: 13, color: '#374151',
                  borderBottom: '1px solid #f1f5f9',
                }}
              >
                <div style={{ fontWeight: 600 }}>{c.channel_code}</div>
                <div style={{ fontSize: 11, color: '#64748b' }}>{c.channel_name} ({c.uom_symbol})</div>
              </button>
            ))}
          </div>
        </div>

        {/* Threshold editor */}
        <div style={{ flex: 1 }}>
          {ch && current && (
            <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: 15 }}>{ch.channel_code} Thresholds</h3>
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                    Version {current.profile_version} • Units: {ch.uom_symbol}
                    {current.changed_by_username && ` • Last changed by ${current.changed_by_username}`}
                  </div>
                </div>
                {!editing && (
                  <button onClick={() => setEditing(true)}
                    style={{ padding: '7px 14px', background: '#1e40af', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
                    Edit Thresholds
                  </button>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                {thresholdFields.map(f => (
                  <div key={f.key} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{
                      width: 12, height: 12, borderRadius: '50%',
                      background: f.color, flexShrink: 0,
                    }} />
                    <label style={{ fontSize: 13, color: '#374151', minWidth: 80 }}>{f.label}</label>
                    {editing ? (
                      <input
                        type="number" step="any"
                        value={editValues[f.key] ?? ''}
                        onChange={e => setEditValues(prev => ({ ...prev, [f.key]: e.target.value }))}
                        placeholder="(unset)"
                        style={{ width: 100, padding: '5px 8px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 }}
                      />
                    ) : (
                      <span style={{ fontWeight: 600, fontFamily: 'monospace', fontSize: 13 }}>
                        {(current as any)[f.key] ?? '—'} {(current as any)[f.key] !== null ? ch.uom_symbol : ''}
                      </span>
                    )}
                  </div>
                ))}
              </div>

              {editing && (
                <div>
                  <div style={{ marginBottom: 12 }}>
                    <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>
                      Change Reason <span style={{ color: '#ef4444' }}>*</span>
                    </label>
                    <textarea
                      value={changeReason}
                      onChange={e => setChangeReason(e.target.value)}
                      rows={2} required
                      placeholder="Describe the reason for this threshold change..."
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13, resize: 'vertical' }}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={handleSaveClick}
                      style={{ padding: '8px 18px', background: '#1e40af', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
                      Save (requires signature)
                    </button>
                    <button onClick={() => setEditing(false)}
                      style={{ padding: '8px 14px', background: '#e2e8f0', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Version history */}
          {profiles.length > 1 && (
            <div style={{ marginTop: 16, background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid #e2e8f0', fontSize: 13, fontWeight: 600, color: '#374151' }}>
                Threshold Version History
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                    {['Version', 'Effective From', 'Alert', 'Alarm', 'Danger', 'Changed By', 'Reason'].map(h => (
                      <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#374151', fontSize: 11 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {profiles.map(p => (
                    <tr key={p.profile_id} style={{ borderBottom: '1px solid #f1f5f9', background: p.is_current ? '#f0fdf4' : 'transparent' }}>
                      <td style={{ padding: '7px 10px', fontWeight: p.is_current ? 600 : 400 }}>v{p.profile_version}{p.is_current ? ' ✓' : ''}</td>
                      <td style={{ padding: '7px 10px', fontFamily: 'monospace', fontSize: 11 }}>{p.effective_from.replace('T', ' ').slice(0, 16)}</td>
                      <td style={{ padding: '7px 10px' }}>{p.alert_threshold ?? '—'}</td>
                      <td style={{ padding: '7px 10px' }}>{p.alarm_threshold ?? '—'}</td>
                      <td style={{ padding: '7px 10px' }}>{p.danger_threshold ?? '—'}</td>
                      <td style={{ padding: '7px 10px', color: '#64748b' }}>{p.changed_by_username || '—'}</td>
                      <td style={{ padding: '7px 10px', color: '#64748b', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.change_reason || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {showSignModal && (
        <SignatureModal
          isOpen={true}
          title="Sign Threshold Change"
          meaning={`I approve this threshold change for channel ${ch?.channel_code}. Reason: ${changeReason}`}
          username={user?.username || ''}
          onConfirm={handleSignConfirm}
          onCancel={() => { setShowSignModal(false); setPendingPayload(null); }}
          requireComment={false}
        />
      )}
    </div>
  );
};
