import { useEffect, useMemo, useRef, useState } from 'react';
import styles from './IndexingPage.module.css';
import { MenuIcon, RefreshIcon } from '../shared/Icons';
import FolderSelector from './FolderSelector';
import ProgressTracker from './ProgressTracker';
import ActivityFeed from './ActivityFeed';
import FileExplorerPreview from './FileExplorerPreview';
import { cancelIndexJob, fetchProgress, scanFolder, fetchInsightsRecentFiles } from '../../services/api';
import { socketService } from '../../services/socketService';
import { useProgress } from '../../context/ProgressContext';

function basename(p) {
  if (!p) return '';
  const parts = String(p).split(/[\\/]/);
  return parts[parts.length - 1];
}

export default function IndexingPage({ onToggleSidebar }) {
  const [folderPath, setFolderPath] = useState('');
  const [pickedFiles, setPickedFiles] = useState([]); // webkitRelativePath strings
  const [pickedFolderName, setPickedFolderName] = useState('');
  const [pickedCount, setPickedCount] = useState(0);
  const [uiError, setUiError] = useState('');
  const [recent, setRecent] = useState([]);

  const fileInputRef = useRef(null);
  const unsubRef = useRef(null);

  const { state, dispatch } = useProgress();
  const activeJobId = state.activeJobId;
  const progress = activeJobId ? state.jobs[activeJobId] : null;

  const isRunning = !!(
    progress && ['scanning', 'processing', 'embedding', 'indexing'].includes(progress.status)
  );

  const statusLabel = isRunning ? 'Running' : 'Idle';

  const currentBase = useMemo(() => basename(progress?.current_file), [progress?.current_file]);

  const loadRecent = async () => {
    try {
      const rows = await fetchInsightsRecentFiles(10);
      setRecent(Array.isArray(rows) ? rows : []);
    } catch (_) {
      // ignore; insights might be empty/not available yet
    }
  };

  useEffect(() => {
    loadRecent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (progress?.status === 'completed') loadRecent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [progress?.status]);

  useEffect(() => {
    return () => {
      try {
        unsubRef.current?.();
      } catch (_) {
        // ignore
      }
      socketService.disconnect();
    };
  }, []);

  const onBrowse = () => fileInputRef.current?.click();

  const onFolderPicked = (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const relPaths = Array.from(files).map((f) => f.webkitRelativePath || f.name).filter(Boolean);
    const first = relPaths[0];
    const rootFolder = first.split('/')[0];
    setPickedFolderName(rootFolder);
    setPickedCount(relPaths.length);
    setPickedFiles(relPaths);
    // Keep UX similar to previous: user still needs absolute path for backend scan.
    if (!folderPath) setFolderPath(rootFolder);
    setUiError('');
    e.target.value = '';
  };

  const connectJob = (jobId) => {
    socketService.connect(jobId);
    unsubRef.current?.();
    unsubRef.current = socketService.subscribe((evt) =>
      dispatch({ type: 'PROGRESS_UPDATE', payload: evt })
    );
    fetchProgress(jobId)
      .then((evt) => dispatch({ type: 'PROGRESS_UPDATE', payload: evt }))
      .catch(() => null);
  };

  const onStart = async () => {
    const trimmed = folderPath.trim();
    if (!trimmed) return;
    setUiError('');
    try {
      const res = await scanFolder(trimmed);
      const jobId = res?.job_id;
      if (!jobId) throw new Error('No job_id returned from server');
      dispatch({ type: 'JOB_STARTED', jobId });
      connectJob(jobId);
    } catch (e) {
      setUiError(e?.message || 'Failed to start indexing');
    }
  };

  const onCancel = async () => {
    if (!activeJobId) return;
    setUiError('');
    try {
      await cancelIndexJob(activeJobId);
    } catch (e) {
      setUiError(e?.message || 'Cancel failed');
    }
  };

  const onRefresh = async () => {
    setUiError('');
    await loadRecent();
    if (activeJobId) connectJob(activeJobId);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <button className={styles.iconBtn} onClick={onToggleSidebar} aria-label="Toggle sidebar">
            <MenuIcon size={17} />
          </button>
          <div className={styles.headerText}>
            <div className={styles.titleRow}>
              <h1 className={styles.title}>Index Documents</h1>
              <span className={`${styles.statusPill} ${isRunning ? styles.running : styles.idle}`}>
                {statusLabel}
              </span>
            </div>
            <p className={styles.subtitle}>Scan, process, and index files into the AI system</p>
          </div>
        </div>

        <button className={styles.refreshBtn} onClick={onRefresh} type="button">
          <RefreshIcon size={16} />
          Refresh
        </button>
      </div>

      <div className={styles.body}>
        {uiError ? <div className={styles.error}>{uiError}</div> : null}

        <input
          ref={fileInputRef}
          type="file"
          webkitdirectory=""
          directory=""
          multiple
          style={{ display: 'none' }}
          onChange={onFolderPicked}
        />

        <div className={styles.grid}>
          <div className={styles.leftCol}>
            <FolderSelector
              folderPath={folderPath}
              setFolderPath={setFolderPath}
              onBrowse={onBrowse}
              onStart={onStart}
              isRunning={isRunning}
              pickedFolderName={pickedFolderName}
              pickedCount={pickedCount}
            />

            <ProgressTracker progress={progress} isRunning={isRunning} onCancel={onCancel} />

            <ActivityFeed logs={progress?.logs || []} />
          </div>

          <div className={styles.rightCol}>
            <FileExplorerPreview
              folderName={pickedFolderName}
              files={pickedFiles}
              currentFileBase={currentBase}
            />

            <div className={styles.card}>
              <div className={styles.cardTitle}>Recent Indexed Files</div>
              <div className={styles.recentList}>
                {recent.length === 0 ? (
                  <div className={styles.muted}>No recent files yet.</div>
                ) : (
                  recent.slice(0, 10).map((r, idx) => (
                    <div key={`${r.file_name}-${idx}`} className={styles.recentRow}>
                      <div className={styles.recentName} title={r.file_name || ''}>
                        {r.file_name || '—'}
                      </div>
                      <div className={styles.recentMeta}>
                        <span className={styles.typePill}>{(r.file_type || 'others').toUpperCase()}</span>
                        <span className={styles.time}>
                          {r.indexed_at ? new Date(r.indexed_at).toLocaleString() : '—'}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className={styles.card}>
              <div className={styles.cardTitle}>System Status</div>
              <div className={styles.statusGrid}>
                <div className={styles.kv}>
                  <div className={styles.k}>Queue</div>
                  <div className={styles.v}>
                    {progress?.total_files ? Math.max((progress.total_files || 0) - (progress.processed_files || 0), 0) : '—'}
                  </div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.k}>Speed</div>
                  <div className={styles.v}>
                    {progress?.started_at && progress?.processed_files != null
                      ? `${(
                          (progress.processed_files || 0) /
                          Math.max((Date.now() / 1000) - progress.started_at, 1)
                        ).toFixed(2)} files/s`
                      : '—'}
                  </div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.k}>Active Job</div>
                  <div className={styles.vMono}>{activeJobId ? activeJobId.slice(0, 10) : '—'}</div>
                </div>
              </div>
              <div className={styles.muted}>
                System load metrics are not available yet.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

