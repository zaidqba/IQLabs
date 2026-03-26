/**
 * IQ-RAD API Client
 * Axios instance with JWT interceptor and automatic token refresh.
 * All API calls include X-Request-ID for audit trail correlation.
 */
import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(access: string, refresh: string): void {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem('iq_rad_access', access);
  localStorage.setItem('iq_rad_refresh', refresh);
}

export function clearTokens(): void {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem('iq_rad_access');
  localStorage.removeItem('iq_rad_refresh');
}

export function loadStoredTokens(): void {
  accessToken = localStorage.getItem('iq_rad_access');
  refreshToken = localStorage.getItem('iq_rad_refresh');
}

export function getAccessToken(): string | null {
  return accessToken;
}

const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Attach JWT
api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// Refresh on 401
let isRefreshing = false;
let failedQueue: Array<{ resolve: (v: unknown) => void; reject: (e: unknown) => void }> = [];

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && !originalRequest._retry && refreshToken) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers = { ...originalRequest.headers, Authorization: `Bearer ${token}` };
          return api(originalRequest);
        });
      }
      originalRequest._retry = true;
      isRefreshing = true;
      try {
        const resp = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refreshToken });
        const newAccess = resp.data.access_token;
        const newRefresh = resp.data.refresh_token;
        setTokens(newAccess, newRefresh);
        processQueue(null, newAccess);
        originalRequest.headers = { ...originalRequest.headers, Authorization: `Bearer ${newAccess}` };
        return api(originalRequest);
      } catch (err) {
        processQueue(err, null);
        clearTokens();
        window.location.href = '/login';
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

export default api;
