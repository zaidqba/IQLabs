/**
 * Reports page — generate, view, and approve compliance reports.
 * Report approval requires electronic signature (21 CFR Part 11).
 */
import React, { useEffect, useState } from 'react';
import { SignatureModal } from '../components/common/SignatureModal';
import { useAuthStore } from '../store/authStore';
import api from '../services/api';
import { format } from 'date-fns';

interface Report {
  report_id: number;
  report_type: string;
  report_title: string;
  period_start: string;
  period_end: string;
  generated_at: string;
  review_state: string;
  generated_by_username: string;
  file_size_bytes: number | null;
}

const REPORT_TYPES = [
  { value: 'DAILY_MONITORING', label: 'Daily Monitoring Report' },
  { value: 'WEEKLY_SUMMARY', label: 'Weekly Summary Report' },
  { value: 'MONTHLY_COMPLIANCE', label: 'Monthly Compliance Report' },
  { value: 'ALARM_HISTORY', label: 'Alarm History Report' },
  { value: 'CALIBRATION_STATUS', label: 'Calibration Status Report' },
];

const STATE_COLOR: Record<string, string> = {
  PENDING_REVIEW: '#f59e0b',
  REVIEWED: '#3b82f6',
  APPROVED: '#16a34a',
  SUPERSEDED: '#9ca3af',
};

export const Reports: React.FC = () => {
  const { user } = useAuthStore();
  const [reports, setReports] = useState<Report[]>([]);
  const [generating, setGenerating] = useState(false);
  const [reportType, setReportType] = useState('DAILY_MONITORING');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [approveTarget, setApproveTarget] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = async () => {
    const resp = await api.get<Report[]>('/reports?limit=50');
    setReports(resp.data);
  };

  useEffect(() => {
    fetchReports();
    // Default date range: yesterday
    const end = new Date();
    const start = new Date(end);
    start.setDate(start.getDate() - 1);
    setPeriodStart(start.toISOString().split('T')[0]);
    setPeriodEnd(end.toISOString().split('T')[0]);
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      await api.post('/reports/generate', {
        report_type: reportType,
        period_start: periodStart,
        period_end: periodEnd,
      });
      await fetchReports();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const handleApprove = async (password: string, comment?: string) => {
    if (!approveTarget) return;
    await api.post(`/reports/${approveTarget.report_id}/approve`, {
      signature_password: password,
      comment: comment || '',
      meaning: `I approve report "${approveTarget.report_title}" and certify the data is accurate and complete.`,
    });
    setApproveTarget(null);
    await fetchReports();
  };

  const handleDownload = async (reportId: number) => {
    const resp = await api.get(`/reports/${reportId}/download`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([resp.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `report_${reportId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return (
    <div>
      <h1 style={{ margin: '0 0 20px', fontSize: 20, color: '#1e293b' }}>Reports</h1>

      {/* Generation form */}
      <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 20, marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 14px', fontSize: 14, color: '#374151' }}>Generate New Report</h3>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>Report Type</label>
            <select value={reportType} onChange={e => setReportType(e.target.value)}
              style={{ padding: '7px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 }}>
              {REPORT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>Period Start</label>
            <input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)}
              style={{ padding: '7px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 }} />
          </div>
          <div>
            <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>Period End</label>
            <input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)}
              style={{ padding: '7px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 }} />
          </div>
          <button
            onClick={handleGenerate} disabled={generating}
            style={{ padding: '7px 18px', background: '#1e40af', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}
          >
            {generating ? 'Generating…' : 'Generate'}
          </button>
        </div>
        {error && <div style={{ color: '#ef4444', fontSize: 12, marginTop: 8 }}>{error}</div>}
      </div>

      {/* Report list */}
      <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
              {['Title', 'Period', 'Generated', 'By', 'State', 'Actions'].map(h => (
                <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', fontSize: 12 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {reports.length === 0 && (
              <tr><td colSpan={6} style={{ padding: 20, textAlign: 'center', color: '#9ca3af' }}>No reports yet</td></tr>
            )}
            {reports.map(r => (
              <tr key={r.report_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={{ padding: '9px 12px' }}>{r.report_title}</td>
                <td style={{ padding: '9px 12px', color: '#64748b', fontSize: 12 }}>
                  {r.period_start.split('T')[0]} → {r.period_end.split('T')[0]}
                </td>
                <td style={{ padding: '9px 12px', color: '#64748b', fontSize: 12 }}>
                  {format(new Date(r.generated_at), 'yyyy-MM-dd HH:mm')}
                </td>
                <td style={{ padding: '9px 12px', color: '#64748b' }}>{r.generated_by_username}</td>
                <td style={{ padding: '9px 12px' }}>
                  <span style={{
                    color: STATE_COLOR[r.review_state] || '#64748b',
                    fontWeight: 600, fontSize: 11,
                  }}>
                    {r.review_state}
                  </span>
                </td>
                <td style={{ padding: '9px 12px', display: 'flex', gap: 6 }}>
                  {r.file_size_bytes && (
                    <button onClick={() => handleDownload(r.report_id)}
                      style={{ padding: '3px 8px', background: '#e2e8f0', border: 'none', borderRadius: 3, cursor: 'pointer', fontSize: 11 }}>
                      Download
                    </button>
                  )}
                  {r.review_state === 'PENDING_REVIEW' && (
                    <button onClick={() => setApproveTarget(r)}
                      style={{ padding: '3px 8px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 3, cursor: 'pointer', fontSize: 11 }}>
                      Approve
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {approveTarget && (
        <SignatureModal
          isOpen={true}
          title="Approve Report"
          meaning={`I approve report "${approveTarget.report_title}" and certify the data is accurate and complete.`}
          username={user?.username || ''}
          onConfirm={handleApprove}
          onCancel={() => setApproveTarget(null)}
          requireComment={true}
        />
      )}
    </div>
  );
};
