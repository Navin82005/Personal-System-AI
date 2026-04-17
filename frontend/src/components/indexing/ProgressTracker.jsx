import styles from './ProgressTracker.module.css';

export default function ProgressTracker({ progress, isRunning, onCancel }) {
  const pct = progress?.progress_percentage ?? 0;
  const status = progress?.status || 'idle';
  const currentFile = progress?.current_file || '';
  const processed = progress?.processed_files ?? 0;
  const total = progress?.total_files ?? 0;
  const message = progress?.message || '';

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.cardTitle}>Indexing Progress</div>
        <span className={`${styles.statePill} ${styles[`state_${status}`] || ''}`}>{status}</span>
      </div>

      <div className={styles.top}>
        <div
          className={styles.ring}
          style={{
            background: `conic-gradient(var(--accent-color) ${pct}%, rgba(255,255,255,0.10) 0)`,
          }}
          aria-label="Progress"
        >
          <div className={styles.ringInner}>{pct}%</div>
        </div>

        <div className={styles.meta}>
          <div className={styles.line}>
            <span className={styles.label}>Files</span>
            <span className={styles.value}>
              {processed} / {total}
            </span>
          </div>
          <div className={styles.current} title={currentFile}>
            {currentFile ? `Current: ${currentFile}` : 'Current: —'}
          </div>
          <div className={styles.bar} aria-hidden="true">
            <div className={styles.fill} style={{ width: `${pct}%` }} />
          </div>
          <div className={styles.message}>{message || '—'}</div>
        </div>
      </div>

      <div className={styles.actions}>
        <button type="button" className={styles.cancelBtn} onClick={onCancel} disabled={!isRunning}>
          Cancel / Stop
        </button>
      </div>
    </div>
  );
}

