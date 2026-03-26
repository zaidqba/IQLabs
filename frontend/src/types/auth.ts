import { UserRole } from './common';
export type { UserRole };

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_seconds: number;
  user_id: number;
  username: string;
  role: UserRole;
}

export interface UserInfo {
  user_id: number;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_locked: boolean;
}
