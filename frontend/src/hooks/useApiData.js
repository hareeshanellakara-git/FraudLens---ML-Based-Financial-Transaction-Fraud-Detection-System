import { useCallback, useEffect, useState } from 'react';
import { apiGet } from '../api/client.js';

const DATA_CHANGED_EVENT = 'fraudlens:data-changed';

export default function useApiData(path, query = {}, enabled = true) {
  const queryKey = JSON.stringify(query);
  const [revision, setRevision] = useState(0);
  const [requestState, setRequestState] = useState({ key: null, data: null, error: null, loading: false });
  const requestKey = `${path || ''}\u0000${queryKey}\u0000${revision}`;

  const reload = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    if (!enabled || !path) {
      setRequestState({ key: requestKey, data: null, error: null, loading: false });
      return undefined;
    }

    const controller = new AbortController();
    let active = true;
    setRequestState({ key: requestKey, data: null, error: null, loading: true });
    apiGet(path, JSON.parse(queryKey), { signal: controller.signal })
      .then((result) => {
        if (active) setRequestState({ key: requestKey, data: result, error: null, loading: false });
      })
      .catch((requestError) => {
        if (active && requestError.name !== 'AbortError') {
          setRequestState({ key: requestKey, data: null, error: requestError, loading: false });
        }
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [enabled, path, queryKey, requestKey]);

  useEffect(() => {
    window.addEventListener(DATA_CHANGED_EVENT, reload);
    return () => window.removeEventListener(DATA_CHANGED_EVENT, reload);
  }, [reload]);

  const current = requestState.key === requestKey;
  return {
    data: current ? requestState.data : null,
    error: current ? requestState.error : null,
    loading: enabled && Boolean(path) && (!current || requestState.loading),
    reload,
  };
}
