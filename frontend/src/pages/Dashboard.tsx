/**
 * Live Dashboard — real-time channel readings via WebSocket.
 * Displays ChannelCards for all known channels, AlarmBanner for active alarms,
 * and a device connectivity summary.
 */
import React, { useEffect, useState } from 'react';
import { useReadingsStore } from '../store/readingsStore';
import { useAlarmStore } from '../store/alarmStore';
import { ChannelCard } from '../components/dashboard/ChannelCard';
import { AlarmBanner } from '../components/dashboard/AlarmBanner';
import api from '../services/api';

interface Channel {
  channel_id: number;
  channel_code: string;
  channel_name: string;
  uom_symbol: string;
  device_name: string;
  is_active: boolean;
}

interface DeviceStatus {
  device_id: number;
  device_name: string;
  connection_state: string;
  last_packet_at: string | null;
}

export const Dashboard: React.FC = () => {
  const { latestReadings } = useReadingsStore();
  const { activeAlarms } = useAlarmStore();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [deviceStatuses, setDeviceStatuses] = useState<DeviceStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInit = async () => {
      try {
        const [chResp, devResp, alarmResp] = await Promise.all([
          api.get<Channel[]>('/channels'),
          api.get<DeviceStatus[]>('/devices'),
          api.get<any[]>('/alarms/active'),
        ]);
        setChannels(chResp.data);
        setDeviceStatuses(devResp.data);
        useAlarmStore.getState().setActiveAlarms(alarmResp.data);
      } finally {
        setLoading(false);
      }
    };
    fetchInit();
  }, []);

  const activeCount = activeAlarms.filter(a => a.alarm_state === 'ACTIVE').length;

  if (loading) {
    return <div style={{ color: '#64748b', padding: 32 }}>Loading channels…</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 20, color: '#1e293b' }}>Live Dashboard</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          {deviceStatuses.map(ds => (
            <span key={ds.device_id} style={{
              padding: '3px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600,
              background: ds.connection_state === 'CONNECTED' ? '#dcfce7' : '#fee2e2',
              color: ds.connection_state === 'CONNECTED' ? '#166534' : '#991b1b',
            }}>
              {ds.device_name}: {ds.connection_state}
            </span>
          ))}
        </div>
      </div>

      <AlarmBanner />

      {activeCount === 0 && (
        <div style={{
          background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 6,
          padding: '8px 14px', marginBottom: 16, fontSize: 13, color: '#166534',
        }}>
          All channels nominal — no active alarms
        </div>
      )}

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
        gap: 14,
      }}>
        {channels.filter(c => c.is_active).map(ch => (
          <ChannelCard
            key={ch.channel_id}
            channel={ch}
            reading={latestReadings.get(ch.channel_code)}
          />
        ))}
      </div>
    </div>
  );
};
