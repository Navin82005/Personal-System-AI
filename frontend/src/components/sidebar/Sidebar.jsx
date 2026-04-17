import styles from './Sidebar.module.css';
import { PlusIcon, ChatIcon, SparklesIcon, InsightsIcon, FolderIcon } from '../shared/Icons';

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  isCollapsed,
  activeView,
  onNavigate,
}) {
  return (
    <aside className={`${styles.sidebar} ${isCollapsed ? styles.collapsed : ''}`}>
      {/* Logo */}
      <div className={styles.logoRow}>
        <div className={styles.logoIcon}>
          <SparklesIcon size={17} />
        </div>
        <span className={styles.logoText}>Personal AI</span>
      </div>

      {/* Primary navigation */}
      <div className={styles.primaryNav}>
        <button
          type="button"
          className={`${styles.navItem} ${activeView === 'chat' ? styles.active : ''}`}
          onClick={() => onNavigate?.('chat')}
        >
          <span className={styles.sessionIcon}>
            <ChatIcon size={14} />
          </span>
          <span className={styles.sessionTitle}>Chat</span>
        </button>

        <button
          type="button"
          className={`${styles.navItem} ${activeView === 'insights' ? styles.active : ''}`}
          onClick={() => onNavigate?.('insights')}
        >
          <span className={styles.sessionIcon}>
            <InsightsIcon size={14} />
          </span>
          <span className={styles.sessionTitle}>Insights</span>
        </button>

        <button
          type="button"
          className={`${styles.navItem} ${activeView === 'indexing' ? styles.active : ''}`}
          onClick={() => onNavigate?.('indexing')}
        >
          <span className={styles.sessionIcon}>
            <FolderIcon size={14} />
          </span>
          <span className={styles.sessionTitle}>Indexing</span>
        </button>
      </div>

      {/* Sessions */}
      <div className={styles.sessionsHeader}>
        <span className={styles.sectionLabel}>Chats</span>
        <button className={styles.newChatBtn} onClick={onNewChat} type="button" title="New chat">
          <PlusIcon size={15} />
          New
        </button>
      </div>
      <div className={styles.sessionList}>
        {sessions.map((session) => (
          <button
            key={session.id}
            type="button"
            className={`${styles.sessionItem} ${activeView === 'chat' && session.id === activeSessionId ? styles.active : ''
              }`}
            onClick={() => {
              onSelectSession(session.id);
              onNavigate?.('chat');
            }}
            aria-current={activeView === 'chat' && session.id === activeSessionId ? 'page' : undefined}
            title={session.title}
          >
            <span className={styles.sessionIcon}>
              <ChatIcon size={14} />
            </span>
            <span className={styles.sessionTitle}>{session.title}</span>
          </button>
        ))}
      </div>

      {/* Footer */}
      <div className={styles.footer}>
        <p className={styles.footerText}>Personal System AI · Local</p>
      </div>
    </aside>
  );
}
