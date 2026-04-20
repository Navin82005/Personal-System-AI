const textDecoder = new TextDecoder();

function getLiveKitClient() {
  // Best-effort: depends on the UMD bundle's global export name.
  return (
    window.livekitClient ||
    window.LivekitClient ||
    window.LiveKitClient ||
    window.livekit ||
    null
  );
}

class LivekitVoiceService {
  constructor() {
    this.room = null;
    this.audioEl = null;
    this.subscribers = new Set();
  }

  subscribe(cb) {
    this.subscribers.add(cb);
    return () => this.subscribers.delete(cb);
  }

  _emit(evt) {
    for (const cb of Array.from(this.subscribers)) {
      try {
        cb(evt);
      } catch (_) {
        // ignore subscriber errors
      }
    }
  }

  async connect({ livekitUrl, token }) {
    const lk = getLiveKitClient();
    if (!lk) {
      throw new Error(
        'LiveKit client not loaded. The CDN script may be blocked/offline. ' +
          'Verify `frontend/index.html` loads livekit-client and refresh.'
      );
    }

    // Support either exported `connect()` or `Room` constructor.
    if (typeof lk.connect === 'function') {
      this.room = await lk.connect(livekitUrl, token, { autoSubscribe: true });
    } else if (lk.Room) {
      const room = new lk.Room();
      await room.connect(livekitUrl, token, { autoSubscribe: true });
      this.room = room;
    } else {
      throw new Error('LiveKit client API not found on global object.');
    }

    this._wireEvents(lk);
    await this._enableMic(lk);
    this._emit({ type: 'status', status: 'listening' });
  }

  async disconnect() {
    try {
      if (this.audioEl) {
        this.audioEl.pause();
        this.audioEl.srcObject = null;
        this.audioEl.remove();
      }
    } catch (_) {
      // ignore
    }
    this.audioEl = null;

    try {
      await this.room?.disconnect?.();
    } catch (_) {
      // ignore
    }
    this.room = null;
    this._emit({ type: 'status', status: 'idle' });
  }

  async _enableMic(lk) {
    // Prefer a one-liner if supported.
    if (this.room?.localParticipant?.setMicrophoneEnabled) {
      await this.room.localParticipant.setMicrophoneEnabled(true);
      return;
    }

    if (typeof lk.createLocalAudioTrack === 'function') {
      const track = await lk.createLocalAudioTrack();
      await this.room.localParticipant.publishTrack(track);
      return;
    }

    throw new Error('Unable to enable microphone with current LiveKit client build.');
  }

  _wireEvents(lk) {
    const RoomEvent = lk.RoomEvent || {};
    const on = this.room?.on?.bind(this.room);
    if (!on) return;

    const dataEvt = RoomEvent.DataReceived || 'dataReceived';
    const trackEvt = RoomEvent.TrackSubscribed || 'trackSubscribed';

    on(dataEvt, (payload /* Uint8Array */, _participant, _kind) => {
      try {
        const jsonText = textDecoder.decode(payload);
        const evt = JSON.parse(jsonText);
        this._emit(evt);
      } catch (_) {
        // ignore invalid payloads
      }
    });

    on(trackEvt, (track, _pub, participant) => {
      const kind = track?.kind || track?.source;
      const isAudio = kind === 'audio' || kind === lk.TrackKind?.Audio || track?.mediaStreamTrack?.kind === 'audio';
      if (!isAudio) return;
      // Ignore user's own audio; the server agent should publish as "personal-ai" by default.
      if (participant?.identity && participant.identity !== 'personal-ai') return;

      try {
        const el = track.attach ? track.attach() : null;
        if (el && el.tagName === 'AUDIO') {
          el.autoplay = true;
          el.style.display = 'none';
          document.body.appendChild(el);
          this.audioEl = el;
        }
      } catch (_) {
        // ignore
      }
    });
  }
}

export const livekitVoiceService = new LivekitVoiceService();
