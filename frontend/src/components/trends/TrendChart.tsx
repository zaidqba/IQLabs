/**
 * Trend Chart — time-series visualization with threshold reference lines.
 * Uses Recharts ComposedChart for combined line + threshold annotations.
 * Each reading is traceable: hover shows ingestion_id for audit reference.
 */
import React from 'react';
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, Brush, ResponsiveContainer, Legend,
} from 'recharts';
import { format } from 'date-fns';
import { Reading } from '../../types/readings';
import { SEVERITY_COLORS } from '../../types/common';

interface ThresholdLines {
  alert?: number;
  alarm?: number;
  danger?: number;
}

interface Props {
  readings: Reading[];
  thresholds?: ThresholdLines;
  channelName: string;
  uomSymbol: string;
}

export const TrendChart: React.FC<Props> = ({ readings, thresholds, channelName, uomSymbol }) => {
  const data = readings.map((r) => ({
    t: new Date(r.measured_at_utc).getTime(),
    value: parseFloat(r.normalized_value),
    quality: r.quality_flag,
    ingestion_id: r.ingestion_id,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', padding: 8, borderRadius: 4, fontSize: 12 }}>
        <div>{format(new Date(d.t), 'yyyy-MM-dd HH:mm:ss')}</div>
        <div><strong>{d.value} {uomSymbol}</strong></div>
        <div style={{ color: '#9ca3af' }}>Ingestion #{d.ingestion_id}</div>
        {d.quality !== 'GOOD' && <div style={{ color: '#f59e0b' }}>Quality: {d.quality}</div>}
      </div>
    );
  };

  return (
    <div>
      <h4 style={{ margin: '0 0 8px', fontSize: 14 }}>{channelName} ({uomSymbol})</h4>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="t"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(t) => format(new Date(t), 'HH:mm')}
            scale="time"
            fontSize={11}
          />
          <YAxis fontSize={11} />
          <Tooltip content={<CustomTooltip />} />
          <Brush dataKey="t" height={20} tickFormatter={(t) => format(new Date(t), 'HH:mm')} />

          {thresholds?.alert && (
            <ReferenceLine y={thresholds.alert} stroke={SEVERITY_COLORS.ALERT}
              strokeDasharray="4 2" label={{ value: 'Alert', fill: SEVERITY_COLORS.ALERT, fontSize: 10 }} />
          )}
          {thresholds?.alarm && (
            <ReferenceLine y={thresholds.alarm} stroke={SEVERITY_COLORS.ALARM}
              strokeDasharray="4 2" label={{ value: 'Alarm', fill: SEVERITY_COLORS.ALARM, fontSize: 10 }} />
          )}
          {thresholds?.danger && (
            <ReferenceLine y={thresholds.danger} stroke={SEVERITY_COLORS.DANGER}
              strokeDasharray="4 2" label={{ value: 'Danger', fill: SEVERITY_COLORS.DANGER, fontSize: 10 }} />
          )}

          <Line type="monotone" dataKey="value" stroke="#3b82f6"
            dot={false} strokeWidth={2} connectNulls />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};
