import { useEffect, useMemo, useState } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import styles from './ChatWindow.module.css';
import { MenuIcon, BrainIcon, MicIcon, MicOffIcon } from '../shared/Icons';
import { sendMessageToBackend } from '../../services/api';
import { fetchLivekitToken, startVoiceSession, stopVoiceSession } from '../../services/api';
import { livekitVoiceService } from '../../services/voice/livekitVoiceService';

const SUGGESTIONS = [
  '📄 Summarize my uploaded documents',
  '🔍 Search for information in my files',
  '💡 What can you help me with?',
  '📊 Explain the key insights from my data',
];

export default function ChatWindow({ session, onAddMessage, isLoading, setIsLoading, onToggleSidebar }) {
  const hasMessages = session?.messages?.length > 0;
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState('idle'); // idle | listening | processing | speaking
  const [liveTranscript, setLiveTranscript] = useState('');

  const roomName = useMemo(() => (session?.id ? `psai-${session.id}` : 'psai-default'), [session?.id]);

  useEffect(() => {
    const unsub = livekitVoiceService.subscribe((evt) => {
      if (evt?.type === 'status') {
        setVoiceStatus(evt.status || 'idle');
      }
      if (evt?.type === 'transcript') {
        setLiveTranscript(evt.text || '');
        if (evt.is_final && evt.text) {
          onAddMessage({
            id: Date.now(),
            sender: 'user',
            text: evt.text,
            timestamp: Date.now(),
          });
        }
      }
      if (evt?.type === 'assistant_text') {
        if (evt.text) {
          onAddMessage({
            id: Date.now() + 1,
            sender: 'ai',
            text: evt.text,
            timestamp: Date.now(),
          });
        }
      }
    });
    return () => unsub();
  }, [onAddMessage]);

  const handleSend = async (text) => {
    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text,
      timestamp: Date.now(),
    };
    onAddMessage(userMsg);
    setIsLoading(true);

    try {
      const aiResponse = await sendMessageToBackend(text);
      const aiMsg = {
        id: Date.now() + 1,
        sender: 'ai',
        text: aiResponse,
        timestamp: Date.now(),
      };
      onAddMessage(aiMsg);
    } catch (err) {
      const errMsg = {
        id: Date.now() + 1,
        sender: 'ai',
        text: err.message || 'Something went wrong. Please try again.',
        timestamp: Date.now(),
        isError: true,
      };
      onAddMessage(errMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleVoice = async () => {
    try {
      if (voiceEnabled) {
        setVoiceEnabled(false);
        setVoiceStatus('idle');
        setLiveTranscript('');
        try {
          await stopVoiceSession(roomName);
        } catch (_) {
          // ignore
        }
        await livekitVoiceService.disconnect();
        return;
      }

      setVoiceEnabled(true);
      setVoiceStatus('processing');
      setLiveTranscript('');

      await startVoiceSession(roomName); // ensure backend agent is running

      const participantName = `user-${Math.random().toString(16).slice(2, 8)}`;
      const tok = await fetchLivekitToken(roomName, participantName);
      const livekitUrl = import.meta.env.VITE_LIVEKIT_URL;
      if (!livekitUrl) throw new Error('VITE_LIVEKIT_URL is not set');
      await livekitVoiceService.connect({ livekitUrl, token: tok.token });
    } catch (e) {
      setVoiceEnabled(false);
      setVoiceStatus('idle');
      setLiveTranscript('');
      onAddMessage({
        id: Date.now() + 2,
        sender: 'ai',
        text: `Voice error: ${e?.message || 'Unable to start voice session.'}`,
        timestamp: Date.now(),
        isError: true,
      });
    }
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <button className={styles.toggleBtn} onClick={onToggleSidebar} aria-label="Toggle sidebar">
            <MenuIcon size={17} />
          </button>
          <span className={styles.headerTitle}>
            {session?.title || 'New Chat'}
          </span>
        </div>
        <div className={styles.headerRight}>
          {voiceEnabled ? (
            <span className={styles.voicePill}>
              {voiceStatus}
              {liveTranscript ? ` · ${liveTranscript}` : ''}
            </span>
          ) : null}
          <button
            type="button"
            className={styles.voiceBtn}
            onClick={handleToggleVoice}
            aria-label={voiceEnabled ? 'Disable voice' : 'Enable voice'}
            title={voiceEnabled ? 'Disable voice' : 'Enable voice'}
          >
            {voiceEnabled ? <MicOffIcon size={16} /> : <MicIcon size={16} />}
          </button>
          <span className={styles.headerBadge}>● Online</span>
        </div>
      </div>

      {/* Welcome Screen or Chat */}
      {!hasMessages ? (
        <div className={styles.welcomeScreen}>
          <div className={styles.welcomeGlow}>
            <BrainIcon size={38} />
          </div>
          <h1 className={styles.welcomeTitle}>What can I help you with?</h1>
          <p className={styles.welcomeSubtitle}>
            Your personal AI assistant. Ask me anything about your documents,
            files, or any topic you need help with.
          </p>
          <div className={styles.suggestionsGrid}>
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                type="button"
                className={styles.suggestionCard}
                onClick={() => handleSend(s.replace(/^[\p{Emoji}\s]+/u, '').trim())}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <MessageList messages={session.messages} isLoading={isLoading} />
      )}

      {/* Input */}
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  );
}
