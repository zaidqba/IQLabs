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

const AppWithWS: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, accessToken } = useAuthStore();
  const { updateReading, setNtpStatus } = useReadingsStore();
  const { setActiveAlarms, updateAlarm } = useAlarmStore();

  useEffect(() => {
    if (!isAuthenticated || !accessToken) {
      wsClient.disconnect();
      return;
    }

    wsClient.connect(accessToken);

    wsClient.on('reading', (msg) => updateReading(msg.data));
    wsClient.on('alarm', (msg) => updateAlarm(msg.data));
    wsClient.on('alarms_snapshot', (msg) => setActiveAlarms(msg.data));
    wsClient.on('device_status', () => {});
    wsClient.on('heartbeat', (msg) => setNtpStatus(msg.data?.ntp_valid ?? true));

    return () => {
      wsClient.off('reading');
      wsClient.off('alarm');
      wsClient.off('alarms_snapshot');
      wsClient.off('device_status');
      wsClient.off('heartbeat');
    };
  }, [isAuthenticated, accessToken]);

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
