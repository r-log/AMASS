/**
 * Real-time WebSocket client for instant updates.
 * Connects to backend /ws, subscribes to rooms, and dispatches CustomEvents on window.
 */

const RealtimeClient = {
  ws: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: 10,
  baseReconnectDelay: 1000,
  reconnectTimer: null,
  subscribedRooms: new Set(),

  getWsUrl() {
    const config = window.AppConfig || {};
    const baseUrl = (config.api && config.api.baseUrl) || 'http://localhost:5000/api';
    const url = new URL(baseUrl);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${url.host}/ws`;
  },

  connect(token) {
    if (!token) return;
    this.disconnect();

    const wsUrl = `${this.getWsUrl()}?token=${encodeURIComponent(token)}`;
    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('✅ WebSocket connected');
        // Don't reset reconnectAttempts here — wait for a successful
        // authenticated message. TCP connect succeeds (200) even when
        // the server is about to reject the token.
        this._resubscribe();
      };

      this.ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          const event = msg.event || msg.type;
          const data = msg.data || {};
          if (event === 'error') {
            console.warn('WebSocket error:', data.message);
            if (data.message === 'Unauthorized') {
              // Token is invalid — stop reconnecting, it will never succeed
              this.reconnectAttempts = this.maxReconnectAttempts;
              console.warn('WebSocket auth failed. Will not retry with this token.');
            }
            return;
          }
          // Got a real message — connection is healthy
          this.reconnectAttempts = 0;
          const customEventName = `realtime:${event}`;
          window.dispatchEvent(new CustomEvent(customEventName, { detail: data }));
        } catch (e) {
          console.warn('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onclose = () => {
        this.ws = null;
        if (this.reconnectAttempts < this.maxReconnectAttempts && token) {
          const delay = Math.min(
            this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
            30000
          );
          this.reconnectAttempts += 1;
          console.log(`WebSocket closed. Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`);
          this.reconnectTimer = setTimeout(() => this.connect(token), delay);
        }
      };

      this.ws.onerror = () => {
        // onclose will handle reconnect
      };
    } catch (e) {
      console.error('WebSocket connect failed:', e);
    }
  },

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts; // prevent reconnect
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  },

  subscribe(rooms) {
    const arr = Array.isArray(rooms) ? rooms : [rooms];
    arr.forEach((r) => this.subscribedRooms.add(r));
    this._send({ type: 'subscribe', rooms: arr });
  },

  unsubscribe(rooms) {
    const arr = Array.isArray(rooms) ? rooms : [rooms];
    arr.forEach((r) => this.subscribedRooms.delete(r));
    this._send({ type: 'unsubscribe', rooms: arr });
  },

  _resubscribe() {
    if (this.subscribedRooms.size > 0) {
      this._send({ type: 'subscribe', rooms: [...this.subscribedRooms] });
    }
  },

  _send(msg) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  },
};

window.RealtimeClient = RealtimeClient;
console.log('🔌 Realtime WebSocket client loaded');

// Connect if authManager already has a token (e.g. script load order)
if (window.authManager && window.authManager.isAuthenticated()) {
  RealtimeClient.connect(window.authManager.getToken());
}
