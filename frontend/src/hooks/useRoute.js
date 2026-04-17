import { useEffect, useState } from 'react';

const ROUTES = new Set(['/chat', '/insights', '/indexing']);

function normalize(pathname) {
  if (!pathname) return '/insights';
  if (pathname === '/') return '/insights';
  if (ROUTES.has(pathname)) return pathname;
  return '/insights';
}

export function useRoute() {
  const [pathname, setPathname] = useState(() => normalize(window.location.pathname));

  useEffect(() => {
    const onPop = () => setPathname(normalize(window.location.pathname));
    window.addEventListener('popstate', onPop);

    const normalized = normalize(window.location.pathname);
    if (window.location.pathname !== normalized) {
      window.history.replaceState({}, '', normalized);
      setPathname(normalized);
    }

    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const navigate = (to, { replace = false } = {}) => {
    const next = normalize(to);
    if (replace) window.history.replaceState({}, '', next);
    else window.history.pushState({}, '', next);
    setPathname(next);
  };

  return { pathname, navigate };
}

