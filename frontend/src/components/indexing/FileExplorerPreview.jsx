import { useMemo } from 'react';
import styles from './FileExplorerPreview.module.css';

function buildTree(paths) {
  const root = { name: '', children: new Map(), isFile: false };
  for (const p of paths) {
    const parts = String(p).split('/').filter(Boolean);
    let node = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isFile = i === parts.length - 1;
      if (!node.children.has(part)) {
        node.children.set(part, { name: part, children: new Map(), isFile });
      }
      node = node.children.get(part);
      node.isFile = isFile;
    }
  }
  return root;
}

function flatten(node, depth = 0, out = []) {
  if (!node.children) return out;
  const entries = Array.from(node.children.values()).sort((a, b) => {
    if (a.isFile !== b.isFile) return a.isFile ? 1 : -1;
    return a.name.localeCompare(b.name);
  });
  for (const child of entries) {
    out.push({ name: child.name, depth, isFile: child.isFile });
    if (!child.isFile) flatten(child, depth + 1, out);
  }
  return out;
}

export default function FileExplorerPreview({ folderName, files, currentFileBase }) {
  const treeRows = useMemo(() => {
    const list = Array.isArray(files) ? files : [];
    if (list.length === 0) return [];
    const tree = buildTree(list);
    return flatten(tree, 0, []);
  }, [files]);

  return (
    <div className={styles.card}>
      <div className={styles.cardTitle}>File Explorer Preview</div>
      {treeRows.length === 0 ? (
        <div className={styles.muted}>Pick a folder to preview its files.</div>
      ) : (
        <>
          <div className={styles.muted}>
            {folderName ? `Folder: ${folderName}` : 'Folder preview'}
          </div>
          <div className={styles.tree}>
            {treeRows.slice(0, 250).map((r, idx) => {
              const isActive = r.isFile && currentFileBase && r.name === currentFileBase;
              return (
                <div
                  key={`${r.name}-${idx}`}
                  className={`${styles.row} ${isActive ? styles.active : ''}`}
                  style={{ paddingLeft: `${8 + r.depth * 14}px` }}
                  title={r.name}
                >
                  <span className={styles.bullet}>{r.isFile ? '•' : '▸'}</span>
                  <span className={styles.name}>{r.name}</span>
                </div>
              );
            })}
            {treeRows.length > 250 ? (
              <div className={styles.muted}>…and {treeRows.length - 250} more</div>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}

