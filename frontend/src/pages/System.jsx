import React from 'react';
import useApiData from '../hooks/useApiData.js';
import { EmptyState, ErrorState, LoadingState } from '../components/PageFeedback.jsx';
import '../styles/Page.css';
import '../styles/System.css';
import '../styles/DataStates.css';

function System() {
  const status = useApiData('/system/status');
  const data = status.data;
  return (
    <div className="page-content">
      <h2>System Status</h2>
      {status.loading && !data && <LoadingState label="Checking live backend status…" />}
      {status.error && <ErrorState error={status.error} onRetry={status.reload} />}
      {data && !status.error && <>
        <section className="status-panel">
          <h3>Backend</h3>
          <p>Database: <span className={`status ${data.db_ok ? 'online' : 'offline'}`}>{data.db_ok ? 'Connected' : 'Unavailable'}</span></p>
          <p>Latest processing sequence: {data.latest_processing_seq}</p>
        </section>
        <section className="status-panel">
          <h3>Model and feature pipeline</h3>
          <dl className="detail-list">
            <dt>Model artifact</dt><dd>{data.model?.model_path || 'Not reported by backend'}</dd>
            <dt>Feature count</dt><dd>{data.model?.feature_count ?? 'Not reported by backend'}</dd>
            <dt>Decision threshold</dt><dd>{data.model?.decision_threshold ?? 'Not reported by backend'}</dd>
            <dt>LOW maximum</dt><dd>{data.model?.risk_policy?.low_max ?? 'Not reported by backend'}</dd>
            <dt>MEDIUM maximum</dt><dd>{data.model?.risk_policy?.medium_max ?? 'Not reported by backend'}</dd>
            <dt>HIGH minimum</dt><dd>{data.model?.risk_policy?.high_min ?? 'Not reported by backend'}</dd>
          </dl>
        </section>
        <section className="status-panel">
          <h3>Stream state</h3>
          {data.stream_state ? <dl className="detail-list"><dt>Next row index</dt><dd>{data.stream_state.row_index}</dd><dt>Last streamed processing sequence</dt><dd>{data.stream_state.cursor}</dd></dl> : <EmptyState title="Stream state unavailable">The status API did not return stream state.</EmptyState>}
        </section>
        {status.loading && <LoadingState label="Refreshing system status…" />}
      </>}
    </div>
  );
}

export default System;
