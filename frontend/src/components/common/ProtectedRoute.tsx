import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { UserRole } from '../../types/auth';

interface Props {
  children: React.ReactNode;
  requiredRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<Props> = ({ children, requiredRoles }) => {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  if (requiredRoles && user && !requiredRoles.includes(user.role as UserRole)) {
    return <div style={{ padding: 32, color: '#ef4444' }}>Access denied: insufficient role.</div>;
  }

  return <>{children}</>;
};
