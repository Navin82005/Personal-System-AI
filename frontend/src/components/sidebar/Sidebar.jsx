import styles from './Sidebar.module.css';
import { PlusIcon, ChatIcon, SparklesIcon } from '../shared/Icons';
import FolderScan from './FolderScan';

export default function Sidebar({ sessions, activeSessionId, onSelectSession, onNewChat, isCollapsed }) {
  return (
    <aside className={`${styles.sidebar} ${isCollapsed ? styles.collapsed : ''}`}>
      {/* Logo */}
      <div className={styles.logoRow}>
        <div className={styles.logoIcon}>
          <SparklesIcon size={17} />
        </div>
        <span className={styles.logoText}>Personal AI</span>
      </div>

      {/* New Chat */}
      <button className={styles.newChatBtn} onClick={onNewChat}>
        <PlusIcon size={15} />
        New Chat
      </button>

      {/* Folder Indexing */}
      <FolderScan />

      {/* Sessions */}
      <span className={styles.sectionLabel}>Recent</span>
      <div className={styles.sessionList}>
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`${styles.sessionItem} ${session.id === activeSessionId ? styles.active : ''}`}
            onClick={() => onSelectSession(session.id)}
          >
            <span className={styles.sessionIcon}>
              <ChatIcon size={14} />
            </span>
            <span className={styles.sessionTitle}>{session.title}</span>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className={styles.footer}>
        <p className={styles.footerText}>Personal System AI · Local</p>
      </div>
    </aside>
  );
}
