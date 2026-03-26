/**
 * IQ-RAD WebSocket Client
 * Connects to /api/v1/ws/live with JWT authentication.
 * Implements automatic reconnect with exponential backoff.
 * Dispatches typed events to registered handlers.
 */
import { getAccessToken } from './api';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws/live';

type WSMessageHandler = (data: Record<string, unknown>) => void;

class IQRadWebSocket {
  private ws: WebSocket | null = null;
  private handlers: Map<string, WSMessageHandler[]> = new Map();
  private reconnectAttempt = 0;
  private running = false;

  connect(): void {
    this.running = true;
    this._connect();
  }

  disconnect(): void {
    this.running = false;
    this.ws?.close();
    this.ws = null;
  }

  on(type: string, handler: WSMessageHandler): () => void {
    if (!this.handlers.has(type)) this.handlers.set(type, []);
    this.handlers.get(type)!.push(handler);
    return () => {
      const arr = this.handlers.get(type) || [];
      this.handlers.set(type, arr.filter((h) => h !== handler));
    };
  }

  private _connect(): void {
    const token = getAccessToken();
    if (!token) return;

    this.ws = new WebSocket(`${WS_URL}?token=${token}`);

    this.ws.onopen = () => {
      this.reconnectAttempt = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>;
        const type = data.type as string;
        const handlers = this.handlers.get(type) || [];
        const allHandlers = this.handlers.get('*') || [];
        [...handlers, ...allHandlers].forEach((h) => h(data));
      } catch {
        // ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      if (!this.running) return;
      const delay = Math.min(1000 * 2 ** this.reconnectAttempt, 30000);
      this.reconnectAttempt++;
      setTimeout(() => this._connect(), delay);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }
}

export const wsClient = new IQRadWebSocket();
