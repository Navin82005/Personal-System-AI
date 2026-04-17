import { useEffect, useMemo, useState } from 'react';
import styles from './InsightsWindow.module.css';
import { MenuIcon, RefreshIcon } from '../shared/Icons';
import {
  fetchInsightsSummary,
  fetchInsightsContentDistribution,
  fetchInsightsRecentFiles,
  fetchInsightsSizeDistribution,
} from '../../services/api';

const TYPE_LABELS = {
  pdf: 'PDFs',
  code: 'Code Files',
  text: 'Text Files',
  others: 'Others',
};

const SIZE_LABELS = {
  lt_100kb: '< 100 KB',
  '100kb_1mb': '100 KB - 1 MB',
  '1mb_10mb': '1 MB - 10 MB',
  gt_10mb: '> 10 MB',
  unknown: 'Unknown',
};

function toPercent(count, total) {
  if (!total) return 0;
  return Math.round((count / total) * 100);
}

function formatDateTime(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

export default function InsightsWindow({ onToggleSidebar }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [summary, setSummary] = useState(null);
  const [distribution, setDistribution] = useState(null);
  const [sizeBuckets, setSizeBuckets] = useState(null);
  const [recentFiles, setRecentFiles] = useState([]);

  const totalFiles = summary?.total_files ?? 0;
  const contentPercents = useMemo(() => {
    const counts = distribution?.file_types || {};
    return Object.keys(TYPE_LABELS).map((k) => ({
      key: k,
      label: TYPE_LABELS[k],
      count: counts[k] ?? 0,
      percent: toPercent(counts[k] ?? 0, totalFiles),
    }));
  }, [distribution, totalFiles]);

  const sizePercents = useMemo(() => {
    const counts = sizeBuckets?.size_buckets || {};
    return Object.keys(SIZE_LABELS).map((k) => ({
      key: k,
      label: SIZE_LABELS[k],
      count: counts[k] ?? 0,
      percent: toPercent(counts[k] ?? 0, totalFiles),
    }));
  }, [sizeBuckets, totalFiles]);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [s, d, r, sz] = await Promise.all([
        fetchInsightsSummary(),
        fetchInsightsContentDistribution(),
        fetchInsightsRecentFiles(10),
        fetchInsightsSizeDistribution(),
      ]);
      setSummary(s);
      setDistribution(d);
      setRecentFiles(Array.isArray(r) ? r : []);
      setSizeBuckets(sz);
    } catch (e) {
      setError(e?.message || 'Failed to load insights.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <button className={styles.iconBtn} onClick={onToggleSidebar} aria-label="Toggle sidebar">
            <MenuIcon size={17} />
          </button>
          <span className={styles.headerTitle}>Insights</span>
        </div>
        <button className={styles.refreshBtn} onClick={load} disabled={loading}>
          <RefreshIcon size={16} />
          Refresh
        </button>
      </div>

      <div className={styles.body}>
        {error ? (
          <div className={styles.error}>{error}</div>
        ) : null}

        <div className={styles.section}>
          <div className={styles.sectionTitle}>Summary</div>
          <div className={styles.cardsGrid}>
            <div className={styles.card}>
              <div className={styles.cardLabel}>Total Indexed Files</div>
              <div className={styles.cardValue}>{loading ? '—' : summary?.total_files ?? 0}</div>
            </div>
            <div className={styles.card}>
              <div className={styles.cardLabel}>Total Chunks / Embeddings</div>
              <div className={styles.cardValue}>{loading ? '—' : summary?.total_chunks ?? 0}</div>
            </div>
            <div className={styles.card}>
              <div className={styles.cardLabel}>Last Indexed Time</div>
              <div className={styles.cardValueSm}>
                {loading ? '—' : formatDateTime(summary?.last_indexed_at)}
              </div>
            </div>
          </div>
        </div>

        <div className={styles.twoCol}>
          <div className={styles.section}>
            <div className={styles.sectionTitle}>Majority Content Types</div>
            <div className={styles.card}>
              {contentPercents.map((row) => (
                <div key={row.key} className={styles.barRow}>
                  <div className={styles.barTop}>
                    <div className={styles.barLabel}>{row.label}</div>
                    <div className={styles.barMeta}>
                      {row.percent}% <span className={styles.barMetaDim}>({row.count})</span>
                    </div>
                  </div>
                  <div className={styles.barTrack} aria-hidden="true">
                    <div className={styles.barFill} style={{ width: `${row.percent}%` }} />
                  </div>
                </div>
              ))}
              {!loading && totalFiles === 0 ? (
                <div className={styles.empty}>No indexed files yet. Run “Index Documents” to get started.</div>
              ) : null}
            </div>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionTitle}>File Size Breakdown</div>
            <div className={styles.card}>
              {sizePercents.map((row) => (
                <div key={row.key} className={styles.barRow}>
                  <div className={styles.barTop}>
                    <div className={styles.barLabel}>{row.label}</div>
                    <div className={styles.barMeta}>
                      {row.percent}% <span className={styles.barMetaDim}>({row.count})</span>
                    </div>
                  </div>
                  <div className={styles.barTrack} aria-hidden="true">
                    <div className={styles.barFill} style={{ width: `${row.percent}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <div className={styles.sectionTitle}>Recent Index Activity</div>
          <div className={styles.card}>
            <div className={styles.table}>
              <div className={`${styles.row} ${styles.headerRow}`}>
                <div>File</div>
                <div>Type</div>
                <div>Indexed</div>
              </div>
              {(recentFiles || []).map((f, idx) => (
                <div key={`${f.file_name}-${idx}`} className={styles.row}>
                  <div className={styles.fileCell} title={f.file_name || ''}>
                    {f.file_name || '—'}
                  </div>
                  <div className={styles.typePill}>{(f.file_type || 'others').toUpperCase()}</div>
                  <div className={styles.timeCell}>{formatDateTime(f.indexed_at)}</div>
                </div>
              ))}
              {!loading && (!recentFiles || recentFiles.length === 0) ? (
                <div className={styles.empty}>No recent files to show.</div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

