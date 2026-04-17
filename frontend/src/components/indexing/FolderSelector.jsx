import styles from './FolderSelector.module.css';

export default function FolderSelector({
  folderPath,
  setFolderPath,
  onBrowse,
  onStart,
  isRunning,
  pickedFolderName,
  pickedCount,
}) {
  return (
    <div className={styles.card}>
      <div className={styles.cardTitle}>Folder Selection</div>

      <div className={styles.row}>
        <input
          className={styles.input}
          type="text"
          value={folderPath}
          onChange={(e) => setFolderPath(e.target.value)}
          placeholder="Full path e.g. /Users/you/docs"
          disabled={isRunning}
        />
      </div>

      <div className={styles.actions}>
        <button type="button" className={styles.secondaryBtn} onClick={onBrowse} disabled={isRunning}>
          Browse Folder
        </button>
        <button type="button" className={styles.primaryBtn} onClick={onStart} disabled={!folderPath.trim() || isRunning}>
          Start Indexing
        </button>
      </div>

      <div className={styles.hint}>
        {pickedFolderName ? (
          <span>
            Selected: <span className={styles.em}>{pickedFolderName}</span> ({pickedCount} files)
          </span>
        ) : (
          <span>Tip: Use “Browse Folder” to preview files, then paste the absolute path to start indexing.</span>
        )}
      </div>
    </div>
  );
}

