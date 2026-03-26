import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Trends } from './pages/Trends';
import { AlarmConsole } from './pages/AlarmConsole';
import { Reports } from './pages/Reports';
import { AuditTrail } from './pages/AuditTrail';
import { Calibration } from './pages/Calibration';
import { UserManagement } from './pages/UserManagement';
import { Settings } from './pages/Settings';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';
import { useAuthStore } from './store/authStore';
import { wsClient } from './services/websocket';
import { useReadingsStore } from './store/readingsStore';
import { useAlarmStore } from './store/alarmStore';
import type { LatestReading } from './types/readings';
import type { Alarm } from './types/alarms';

const AppWithWS: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const { updateReading, setNtpStatus } = useReadingsStore();
  const { setActiveAlarms, updateAlarm } = useAlarmStore();

  useEffect(() => {
    if (!isAuthenticated) {
      wsClient.disconnect();
      return;
    }

    wsClient.connect();

    const offReading = wsClient.on('reading', (msg) => updateReading(msg.data as LatestReading));
    const offAlarm = wsClient.on('alarm', (msg) => {
      const a = msg.data as Alarm;
      updateAlarm(a.alarm_id, a);
    });
    const offSnapshot = wsClient.on('alarms_snapshot', (msg) => setActiveAlarms(msg.data as Alarm[]));
    const offDevice = wsClient.on('device_status', () => {});
    const offHb = wsClient.on('heartbeat', (msg) => {
      const d = msg.data as { ntp_valid?: boolean; offset_ms?: number };
      setNtpStatus(d?.ntp_valid ?? true, d?.offset_ms ?? null);
    });

    return () => {
      offReading(); offAlarm(); offSnapshot(); offDevice(); offHb();
    };
  }, [isAuthenticated]);

  return <>{children}</>;
};

const App: React.FC = () => (
  <BrowserRouter>
    <AppWithWS>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route path="/" element={
          <ProtectedRoute>
            <AppLayout><Dashboard /></AppLayout>
          </ProtectedRoute>
        } />

        <Route path="/trends" element={
          <ProtectedRoute>
            <AppLayout><Trends /></AppLayout>
          </ProtectedRoute>
        } />

        <Route path="/alarms" element={
          <ProtectedRoute>
            <AppLayout><AlarmConsole /></AppLayout>
          </ProtectedRoute>
        } />

        <Route path="/reports" element={
          <ProtectedRoute requiredRoles={['OPERATOR', 'ADMIN']}>
            <AppLayout><Reports /></AppLayout>
          </ProtectedRoute>
        } />

        <Route path="/audit" element={
          <ProtectedRoute requiredRoles={['OPERATOR', 'ADMIN', 'DEVELOPER']}>
            <AppLayout><AuditTrail /></AppLayout>
          </ProtectedRoute>
        } />

        <Route path="/calibration" element={
          <ProtectedRoute requiredRoles={['EMISSIONS', 'OPERATOR', 'ADMIN']}>
            <AppLayout><Calibration /></AppLayout>
          </ProtectedRoute>
        } />

        <Route path="/users" element={
          <ProtectedRoute requiredRoles={['ADMIN']}>
            <AppLayout><UserManagement /></AppLayout>
          </ProtectedRoute>
        } />

        <Route path="/settings" element={
          <ProtectedRoute requiredRoles={['OPERATOR', 'ADMIN']}>
            <AppLayout><Settings /></AppLayout>
          </ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppWithWS>
  </BrowserRouter>
);

export default App;
