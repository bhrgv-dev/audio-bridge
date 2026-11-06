export type StateListener = (data: any) => void;

class BridgeClient {
  private socket: WebSocket | null = null;
  private url: string = 'ws://127.0.0.1:8765';
  private listeners: Set<StateListener> = new Set();
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private isManuallyClosed: boolean = true;
  public isConnected: boolean = false;

  constructor() {
    // Phase 1: Client ready for Phase 2 backend WebSocket connection
  }

  public connect(url: string = 'ws://127.0.0.1:8765') {
    this.url = url;
    this.isManuallyClosed = false;

    // Clear any pending reconnect
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.socket) {
      if (this.socket.readyState === WebSocket.OPEN) {
        return;
      }
      if (this.socket.readyState === WebSocket.CONNECTING) {
        return;
      }
      // If closing or closed, cleanly nullify before creating new
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onerror = null;
      this.socket.onclose = null;
      this.socket = null;
    }

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        if (this.isManuallyClosed) {
          this.disconnect();
          return;
        }
        this.isConnected = true;
        this.emit({ type: 'WS_STATUS', connected: true });
      };

      this.socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.emit(payload);
        } catch {
          // Non-JSON message received, ignore cleanly
        }
      };

      this.socket.onerror = () => {
        // In browser WebSockets, connection refused fires onerror then onclose
        this.isConnected = false;
        this.emit({ type: 'WS_STATUS', connected: false });
      };

      this.socket.onclose = () => {
        this.isConnected = false;
        this.emit({ type: 'WS_STATUS', connected: false });

        if (!this.isManuallyClosed) {
          this.scheduleReconnect();
        }
      };
    } catch {
      this.isConnected = false;
      this.emit({ type: 'WS_STATUS', connected: false });
      if (!this.isManuallyClosed) {
        this.scheduleReconnect();
      }
    }
  }

  public disconnect() {
    this.isManuallyClosed = true;

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.socket) {
      // Detach listeners so onclose doesn't fire redundant handlers
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onerror = null;
      this.socket.onclose = null;

      try {
        if (
          this.socket.readyState === WebSocket.OPEN ||
          this.socket.readyState === WebSocket.CONNECTING
        ) {
          this.socket.close();
        }
      } catch {
        // Ignore closing errors
      }
      this.socket = null;
    }

    this.isConnected = false;
    this.emit({ type: 'WS_STATUS', connected: false });
  }

  public send(command: string, data: Record<string, any> = {}) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify({ command, ...data }));
      } catch (err) {
        console.warn('[BridgeClient] Failed to send message:', err);
      }
    }
  }

  public subscribe(listener: StateListener) {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private emit(data: any) {
    this.listeners.forEach((listener) => {
      try {
        listener(data);
      } catch (err) {
        console.error('[BridgeClient] Listener exception:', err);
      }
    });
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout || this.isManuallyClosed) {
      return;
    }
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      if (!this.isManuallyClosed && !this.isConnected) {
        this.connect(this.url);
      }
    }, 4000);
  }
}

export const bridgeClient = new BridgeClient();
