import { useState, useRef } from 'react';
import styles from './FolderScan.module.css';
import { scanFolder } from '../../services/api';

export default function FolderScan() {
  const [isOpen, setIsOpen] = useState(false);
  const [folderPath, setFolderPath] = useState('');
  const [folderName, setFolderName] = useState('');
  const [fileCount, setFileCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const fileInputRef = useRef(null);

  const handleBrowse = () => {
    fileInputRef.current?.click();
  };

  const handleFolderSelect = (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // Extract folder name from webkitRelativePath (e.g. "test_data/file.pdf" → "test_data")
    const firstPath = files[0].webkitRelativePath;
    const rootFolder = firstPath.split('/')[0];

    setFolderName(rootFolder);
    setFileCount(files.length);
    setFolderPath(rootFolder); // User will need to provide full path
    setStatus(null);

    // Reset file input so the same folder can be re-selected
    e.target.value = '';
  };

  const handleScan = async () => {
    const trimmed = folderPath.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setStatus(null);

    try {
      const result = await scanFolder(trimmed);
      const processed = result?.files_processed ?? result?.total_files ?? 'unknown';
      setStatus({
        type: 'success',
        message: `✓ Indexed successfully — ${processed} files processed`,
      });
    } catch (err) {
      setStatus({
        type: 'error',
        message: `✗ ${err.message}`,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleScan();
  };

  return (
    <div className={styles.container}>
      {/* Collapsible toggle */}
      <div
        className={`${styles.toggleRow} ${isOpen ? styles.open : ''}`}
        onClick={() => setIsOpen((o) => !o)}
      >
        <span>{isOpen ? '▾' : '▸'}</span>
        <span>Index Documents</span>
      </div>

      {/* Expandable panel */}
      <div className={`${styles.panel} ${isOpen ? styles.expanded : ''}`}>
        {/* Hidden native folder picker */}
        <input
          ref={fileInputRef}
          type="file"
          webkitdirectory=""
          directory=""
          multiple
          style={{ display: 'none' }}
          onChange={handleFolderSelect}
        />

        {/* Browse area */}
        <div className={styles.browseArea} onClick={handleBrowse}>
          <div className={styles.folderIcon}>📁</div>
          {folderName ? (
            <div className={styles.selectedInfo}>
              <span className={styles.selectedName}>{folderName}</span>
              <span className={styles.selectedMeta}>{fileCount} files found</span>
            </div>
          ) : (
            <div className={styles.browseHint}>
              <span className={styles.browseText}>Browse Folder</span>
              <span className={styles.browseSubtext}>Click to open file explorer</span>
            </div>
          )}
        </div>

        {/* Path input — for full/absolute path */}
        <div className={styles.pathRow}>
          <input
            className={styles.input}
            type="text"
            value={folderPath}
            onChange={(e) => setFolderPath(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Full path e.g. /Users/you/docs"
            disabled={loading}
          />
          <button
            className={styles.scanBtn}
            onClick={handleScan}
            disabled={!folderPath.trim() || loading}
          >
            {loading ? 'Scanning…' : 'Scan'}
          </button>
        </div>

        {/* Status feedback */}
        {loading && (
          <div className={`${styles.status} ${styles.loading}`}>
            <span className={styles.spinner} />
            Indexing folder… this may take a moment
          </div>
        )}
        {status && !loading && (
          <div className={`${styles.status} ${styles[status.type]}`}>
            {status.message}
          </div>
        )}
      </div>
    </div>
  );
}
