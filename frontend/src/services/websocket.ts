/**
 * Deep-Space Mission Control — WebSocket Real-Time Subscriber
 * Resilient streaming abstraction with auto-reconnection and event dispatching.
 */

import { WebSocketEvent, WebSocketStatus } from '../types/api';

type EventListener = (event: WebSocketEvent) => void;
type StatusListener = (status: WebSocketStatus) => void;

class MissionControlWebSocket {
  private ws: WebSocket | null = null;
  private status: WebSocketStatus = 'disconnected';
  private eventListeners: Set<EventListener> = new Set();
  private statusListeners: Set<StatusListener> = new Set();
  private reconnectTimer: any = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 5000;
  private shouldReconnect = true;

  constructor() {
    // Lazy connection on first subscribe
  }

  private resolveWsUrl(): string {
    if (import.meta.env.VITE_WS_URL) {
      return import.meta.env.VITE_WS_URL;
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // If in dev proxy mode on port 5173, point to backend port 8000 directly or via proxy /ws
    if (window.location.port === '5173') {
      return `ws://${window.location.hostname}:8000/ws`;
    }
    return `${protocol}//${window.location.host}/ws`;
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.shouldReconnect = true;
    const url = this.resolveWsUrl();
    this.setStatus(this.reconnectAttempts > 0 ? 'reconnecting' : 'disconnected');

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.setStatus('connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as WebSocketEvent;
          this.notifyEvent(parsed);
        } catch {
          // Ignore malformed payloads safely
        }
      };

      this.ws.onclose = () => {
        this.setStatus('disconnected');
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.setStatus('disconnected');
        // Close event will follow and trigger reconnect
      };
    } catch {
      this.setStatus('disconnected');
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.reconnectTimer) {
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), this.maxReconnectDelay);
    this.setStatus('reconnecting');

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  public disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus('disconnected');
  }

  public subscribe(onEvent: EventListener): () => void {
    this.eventListeners.add(onEvent);
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      this.connect();
    }
    return () => {
      this.eventListeners.delete(onEvent);
    };
  }

  public onStatus(onStatus: StatusListener): () => void {
    this.statusListeners.add(onStatus);
    onStatus(this.status);
    return () => {
      this.statusListeners.delete(onStatus);
    };
  }

  public getStatus(): WebSocketStatus {
    return this.status;
  }

  private setStatus(status: WebSocketStatus): void {
    if (this.status !== status) {
      this.status = status;
      this.statusListeners.forEach((listener) => listener(status));
    }
  }

  private notifyEvent(event: WebSocketEvent): void {
    this.eventListeners.forEach((listener) => {
      try {
        listener(event);
      } catch (err) {
        console.error('Error in mission event listener:', err);
      }
    });
  }

  public sendPing(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'ping' }));
    }
  }
}

export const wsService = new MissionControlWebSocket();
