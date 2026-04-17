import { createContext, useContext, useMemo, useReducer } from 'react';

const ProgressContext = createContext(null);

const initialState = {
  activeJobId: null,
  jobs: {}, // jobId -> progress payload
};

function reducer(state, action) {
  switch (action.type) {
    case 'JOB_STARTED': {
      const { jobId } = action;
      return {
        ...state,
        activeJobId: jobId,
        jobs: {
          ...state.jobs,
          [jobId]: {
            job_id: jobId,
            status: 'idle',
            message: 'Starting…',
            progress_percentage: 0,
            processed_files: 0,
            total_files: 0,
            current_file: null,
            logs: [],
          },
        },
      };
    }
    case 'PROGRESS_UPDATE': {
      const evt = action.payload;
      const jobId = evt?.job_id;
      if (!jobId) return state;
      const prev = state.jobs[jobId] || { logs: [] };

      // Prefer server-provided logs, but keep a lightweight append fallback.
      let nextLogs = Array.isArray(evt.logs) ? evt.logs : prev.logs || [];
      if (!Array.isArray(evt.logs) && evt.message) {
        nextLogs = [...nextLogs, { ts: Date.now() / 1000, message: evt.message, status: evt.status }];
        if (nextLogs.length > 80) nextLogs = nextLogs.slice(-80);
      }

      return {
        ...state,
        jobs: {
          ...state.jobs,
          [jobId]: {
            ...prev,
            ...evt,
            logs: nextLogs,
          },
        },
      };
    }
    case 'JOB_CLEARED': {
      return { ...state, activeJobId: null };
    }
    default:
      return state;
  }
}

export function ProgressProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const value = useMemo(
    () => ({
      state,
      dispatch,
    }),
    [state]
  );

  return <ProgressContext.Provider value={value}>{children}</ProgressContext.Provider>;
}

export function useProgress() {
  const ctx = useContext(ProgressContext);
  if (!ctx) throw new Error('useProgress must be used within ProgressProvider');
  return ctx;
}

