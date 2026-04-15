import styles from './TypingIndicator.module.css';
import { BrainIcon } from '../shared/Icons';

export default function TypingIndicator() {
  return (
    <div className={styles.container}>
      <div className={styles.avatar}>
        <BrainIcon size={17} />
      </div>
      <div className={styles.dots}>
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.dot} />
      </div>
    </div>
  );
}
