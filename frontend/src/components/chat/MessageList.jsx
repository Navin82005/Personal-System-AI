import { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import styles from './MessageList.module.css';

export default function MessageList({ messages, isLoading }) {
  const bottomRef = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className={styles.list}>
      <div className={styles.dayDivider}>
        <span className={styles.line} />
        <span className={styles.dayLabel}>Today</span>
        <span className={styles.line} />
      </div>

      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {isLoading && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
