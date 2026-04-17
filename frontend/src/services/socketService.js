const WS_BASE = 'ws://127.0.0.1:8000';

class SocketService {
  constructor() {
    this.ws = null;
    this.jobId = null;
    this.subscribers = new Set();
    this._onMessage = this._onMessage.bind(this);
    this._onClose = this._onClose.bind(this);
    this._onError = this._onError.bind(this);
  }

  connect(jobId) {
    if (!jobId) throw new Error('jobId required');
    if (this.ws && this.jobId === jobId && this.ws.readyState === WebSocket.OPEN) return;
    this.disconnect();

    this.jobId = jobId;
    this.ws = new WebSocket(`${WS_BASE}/ws/progress/${encodeURIComponent(jobId)}`);
    this.ws.addEventListener('message', this._onMessage);
    this.ws.addEventListener('close', this._onClose);
    this.ws.addEventListener('error', this._onError);
  }

  subscribe(cb) {
    this.subscribers.add(cb);
    return () => this.subscribers.delete(cb);
  }

  disconnect() {
    if (this.ws) {
      try {
        this.ws.removeEventListener('message', this._onMessage);
        this.ws.removeEventListener('close', this._onClose);
        this.ws.removeEventListener('error', this._onError);
        this.ws.close();
      } catch (_) {
        // ignore
      }
    }
    this.ws = null;
    this.jobId = null;
  }

  _onMessage(evt) {
    let data;
    try {
      data = JSON.parse(evt.data);
    } catch (_) {
      return;
    }
    for (const cb of Array.from(this.subscribers)) {
      try {
        cb(data);
      } catch (_) {
        // subscriber errors should not break the socket
      }
    }
  }

  _onClose() {
    // no-op; consumer can decide to fallback/poll
  }

  _onError() {
    // no-op; consumer can decide to fallback/poll
  }
}

export const socketService = new SocketService();

