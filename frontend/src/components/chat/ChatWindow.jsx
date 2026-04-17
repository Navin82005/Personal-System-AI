import { useState } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import styles from './ChatWindow.module.css';
import { MenuIcon, BrainIcon } from '../shared/Icons';
import { sendMessageToBackend } from '../../services/api';

const SUGGESTIONS = [
  '📄 Summarize my uploaded documents',
  '🔍 Search for information in my files',
  '💡 What can you help me with?',
  '📊 Explain the key insights from my data',
];

export default function ChatWindow({ session, onAddMessage, isLoading, setIsLoading, onToggleSidebar }) {
  const hasMessages = session?.messages?.length > 0;

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
        <span className={styles.headerBadge}>● Online</span>
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
