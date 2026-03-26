import { create } from 'zustand';
import { UserRole } from '../types/auth';
import { clearTokens, setTokens } from '../services/api';

interface AuthState {
  user: { user_id: number; username: string; role: UserRole } | null;
  isAuthenticated: boolean;
  setUser: (user: AuthState['user'], access: string, refresh: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  setUser: (user, access, refresh) => {
    setTokens(access, refresh);
    set({ user, isAuthenticated: true });
  },
  logout: () => {
    clearTokens();
    set({ user: null, isAuthenticated: false });
  },
}));
