import styles from './MessageBubble.module.css';
import { BrainIcon, UserIcon } from '../shared/Icons';

export default function MessageBubble({ message }) {
  const { sender, text, timestamp, isError } = message;
  const isUser = sender === 'user';

  const formatTime = (ts) => {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`${styles.wrapper} ${styles[sender]}`}>
      <div className={`${styles.avatar} ${isUser ? styles.userAvatar : styles.aiAvatar}`}>
        {isUser ? <UserIcon size={15} /> : <BrainIcon size={17} />}
      </div>
      <div>
        <div className={`${styles.bubble} ${isError ? styles.errorBubble : ''}`}>
          {text}
        </div>
        {timestamp && (
          <div className={styles.timestamp}>{formatTime(timestamp)}</div>
        )}
      </div>
    </div>
  );
}
