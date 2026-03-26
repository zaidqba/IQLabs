/**
 * Trends page — time-series chart for a selected channel over a selected time window.
 * Loads threshold lines from the channel's current alarm profile.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { TrendChart } from '../components/trends/TrendChart';
import { Reading } from '../types/readings';
import api from '../services/api';

interface Channel {
  channel_id: number;
  channel_code: string;
  channel_name: string;
  uom_symbol: string;
}

interface Thresholds {
  alert?: number;
  alarm?: number;
  danger?: number;
}

const TIME_WINDOWS = [
  { label: 'Last 1 hour', hours: 1 },
  { label: 'Last 4 hours', hours: 4 },
  { label: 'Last 12 hours', hours: 12 },
  { label: 'Last 24 hours', hours: 24 },
  { label: 'Last 7 days', hours: 168 },
];

export const Trends: React.FC = () => {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<number | null>(null);
  const [timeWindow, setTimeWindow] = useState(4);
  const [readings, setReadings] = useState<Reading[]>([]);
  const [thresholds, setThresholds] = useState<Thresholds>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get<Channel[]>('/channels').then(r => {
      setChannels(r.data);
      if (r.data.length > 0) setSelectedChannel(r.data[0].channel_id);
    });
  }, []);

  const fetchReadings = useCallback(async () => {
    if (!selectedChannel) return;
    setLoading(true);
    try {
      const end = new Date();
      const start = new Date(end.getTime() - timeWindow * 3600 * 1000);
      const [rResp, tResp] = await Promise.all([
        api.get<Reading[]>(`/channels/${selectedChannel}/readings`, {
          params: {
            start: start.toISOString(),
            end: end.toISOString(),
            limit: 2000,
          },
        }),
        api.get<any>(`/channels/${selectedChannel}/thresholds`),
      ]);
      setReadings(rResp.data);
      const t = tResp.data;
      setThresholds({
        alert: t.alert_threshold ?? undefined,
        alarm: t.alarm_threshold ?? undefined,
        danger: t.danger_threshold ?? undefined,
      });
    } finally {
      setLoading(false);
    }
  }, [selectedChannel, timeWindow]);

  useEffect(() => { fetchReadings(); }, [fetchReadings]);

  const channel = channels.find(c => c.channel_id === selectedChannel);

  return (
    <div>
      <h1 style={{ margin: '0 0 16px', fontSize: 20, color: '#1e293b' }}>Trend Analysis</h1>

      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>Channel</label>
          <select
            value={selectedChannel ?? ''}
            onChange={e => setSelectedChannel(Number(e.target.value))}
            style={{ padding: '7px 12px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 }}
          >
            {channels.map(c => (
              <option key={c.channel_id} value={c.channel_id}>{c.channel_code} — {c.channel_name}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 4 }}>Time Window</label>
          <select
            value={timeWindow}
            onChange={e => setTimeWindow(Number(e.target.value))}
            style={{ padding: '7px 12px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 }}
          >
            {TIME_WINDOWS.map(tw => (
              <option key={tw.hours} value={tw.hours}>{tw.label}</option>
            ))}
          </select>
        </div>
        <button
          onClick={fetchReadings}
          disabled={loading}
          style={{
            marginTop: 18, padding: '7px 16px', background: '#1e40af', color: '#fff',
            border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13,
          }}
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
        <span style={{ marginTop: 18, fontSize: 12, color: '#9ca3af' }}>
          {readings.length.toLocaleString()} readings
        </span>
      </div>

      <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 20 }}>
        {!selectedChannel ? (
          <div style={{ color: '#9ca3af', textAlign: 'center', padding: 40 }}>Select a channel</div>
        ) : readings.length === 0 && !loading ? (
          <div style={{ color: '#9ca3af', textAlign: 'center', padding: 40 }}>No readings for selected window</div>
        ) : (
          <TrendChart
            readings={readings}
            thresholds={thresholds}
            channelName={channel?.channel_name || ''}
            uomSymbol={channel?.uom_symbol || ''}
          />
        )}
      </div>
    </div>
  );
};
