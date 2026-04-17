import styles from './ActivityFeed.module.css';

export default function ActivityFeed({ logs }) {
  const rows = Array.isArray(logs) ? logs.slice(-18) : [];

  return (
    <div className={styles.card}>
      <div className={styles.cardTitle}>Activity</div>
      {rows.length === 0 ? (
        <div className={styles.muted}>No activity yet.</div>
      ) : (
        <div className={styles.feed}>
          {rows.map((l, idx) => (
            <div key={idx} className={styles.row}>
              <span className={styles.dot} />
              <span className={styles.msg}>{l.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

