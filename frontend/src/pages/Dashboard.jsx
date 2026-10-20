import React, { useRef, useState, useEffect } from 'react';
import { apiPost, notifyPersistedDataChanged } from '../api/client.js';
import useApiData from '../hooks/useApiData.js';
import StatCard from '../components/StatCard.jsx';
import TransactionTable from '../components/TransactionTable.jsx';
import RiskBadge from '../components/RiskBadge.jsx';
import { DetailPanel, EmptyState, ErrorState, LoadingState, formatAmount, formatScore, formatTimestamp } from '../components/PageFeedback.jsx';
import '../styles/Page.css';
import '../styles/DataStates.css';

function Dashboard() {
  const overview = useApiData('/dashboard/overview');
  const streamStatus = useApiData('/stream/status');
  const [streamLoading, setStreamLoading] = useState(false);
  const [streamError, setStreamError] = useState(null);
  const [streamResult, setStreamResult] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const streamLockRef = useRef(false);
const [replayRunning, setReplayRunning] = useState(false);
const replayTimerRef = useRef(null);
  const detail = useApiData(selectedId ? `/transactions/${selectedId}` : null, {}, Boolean(selectedId));
const streamExhausted = streamStatus.data?.exhausted || streamResult?.status === 'exhausted';

  async function processNext() {
    if (streamLockRef.current || streamResult?.status === 'exhausted' || streamStatus.data?.exhausted) return;
    streamLockRef.current = true;
    setStreamLoading(true);
    setStreamError(null);
    setStreamResult(null);
    try {
      const response = await apiPost('/stream/next', {});
      const result = response || { status: 'exhausted', message: 'No unseen test transactions remain.' };
      setStreamResult(result);
      if (result?.status === 'scored') notifyPersistedDataChanged();
      else streamStatus.reload();
    } catch (error) {
      setStreamError(error);
    } finally {
      streamLockRef.current = false;
      setStreamLoading(false);
    }
  }
// Effect to handle continuous replay when running
useEffect(() => {
  if (!replayRunning) return;
  // Start interval to process next transaction every second
  const intervalId = setInterval(() => {
    if (streamExhausted) {
      // Stop replay when no more transactions
      setReplayRunning(false);
      clearInterval(intervalId);
      return;
    }
    if (!streamLoading) {
      processNext();
    }
  }, 1000);
  // Cleanup on pause or component unmount
  return () => clearInterval(intervalId);
}, [replayRunning, streamLoading, streamExhausted]);
  const data = overview.data;
  const recentTransactions = Array.isArray(data?.recent_transactions) ? data.recent_transactions : [];

  return (
    <div className="page-content">
      <div className="page-title-row">
        <div><h2>Overview</h2><p className="subtle">Persisted scoring activity · unseen test replay</p></div>
        <div className="replay-controls" style={{ display: 'flex', gap: '8px' }}>
          <button type="button" className="primary-button" onClick={() => { if (!replayRunning) { setReplayRunning(true); processNext(); }}} disabled={streamLoading || streamExhausted}>
            {replayRunning ? 'Running…' : 'Start Replay'}
          </button>
          <button type="button" className="secondary-button" onClick={() => setReplayRunning(false)} disabled={!replayRunning}>
            Pause
          </button>
          <button type="button" className="secondary-button" onClick={processNext} disabled={streamLoading || streamExhausted}>
            Step Once
          </button>
        </div>
      </div>

      {overview.loading && !data && <LoadingState />}
      {overview.error && <ErrorState error={overview.error} onRetry={overview.reload} />}
      {streamStatus.error && <ErrorState error={streamStatus.error} onRetry={streamStatus.reload} />}
      {streamError && <ErrorState error={streamError} onRetry={processNext} />}
      {streamExhausted && <div className="page-state" role="status"><strong>Replay complete</strong><p>No unseen test transactions remain. No transaction was added.</p></div>}
      {streamResult?.status === 'scored' && <div className="page-state stream-success" role="status">
        <strong>Streamed transaction persisted</strong>
        <p>Transaction {streamResult.transaction_id} · source {streamResult.source_txn_id} · user {streamResult.user_id} · {formatAmount(streamResult.amount)}</p>
        <p>Risk {formatScore(streamResult.risk_score)} ({streamResult.risk_level}) · decision {streamResult.decision} · sequence {streamResult.processing_seq}</p>
        <button type="button" className="secondary-button" onClick={() => setSelectedId(streamResult.transaction_id)}>View transaction details</button>
      </div>}

      {data && <>
        <div className="stats-grid">
          <StatCard title="Transactions Analyzed" value={data.transactions_analyzed} />
          <StatCard title="Flagged Transactions" value={data.flagged_transactions} />
          <StatCard title="High Risk" value={data.high_risk} />
          <StatCard title="Avg. Risk Score" value={formatScore(data.average_risk_score)} />
        </div>

        <section className="section">
          <h3>Recent Transactions</h3>
          {overview.loading && <LoadingState label="Refreshing persisted transactions…" />}
          {recentTransactions.length ? <div className="table-wrap"><TransactionTable transactions={recentTransactions} onRowClick={(tx) => setSelectedId(tx.transaction_id)} /></div> : <EmptyState title="No transactions yet">Score a transaction or process the next unseen test row to populate this table.</EmptyState>}
        </section>

        <section className="section">
          <h3>Risk Distribution</h3>
          <div className="risk-distribution">
            {['LOW', 'MEDIUM', 'HIGH'].map((level) => {
              const count = data.risk_distribution?.[level] ?? 0;
              const total = data.transactions_analyzed || 0;
              return <div key={level} className="risk-bar"><RiskBadge level={level} /><div className="distribution-track"><div className={`distribution-fill ${level.toLowerCase()}`} style={{ width: `${total ? (count / total) * 100 : 0}%` }} /></div><strong>{count}</strong></div>;
            })}
          </div>
        </section>

        <section className="section">
          <h3>Behavioral Signal Summary</h3>
          {data.behavioral_signal_summary?.available ? (
            Object.keys(data.behavioral_signal_summary.signals || {}).length ? <ul className="signal-list">{Object.entries(data.behavioral_signal_summary.signals).map(([name, value]) => <li key={name}>{name}: {value}</li>)}</ul> : <EmptyState title="No persisted behavioral signals">The backend has no signal summary to display.</EmptyState>
          ) : <EmptyState title="Unavailable">{data.behavioral_signal_summary?.reason || 'The backend does not provide persisted behavioral signal data.'}</EmptyState>}
        </section>

        {streamStatus.data && <p className="subtle stream-progress">Replay: {streamStatus.data.processed} processed · {streamStatus.data.remaining} remaining of {streamStatus.data.total}. {streamStatus.data.exhausted ? 'Exhausted.' : ''}</p>}
      </>}

      {selectedId !== null && <DetailPanel title={`Transaction ${selectedId}`} onClose={() => setSelectedId(null)} loading={detail.loading} error={detail.error} onRetry={detail.reload}>
        {detail.data && <dl className="detail-list">
          <dt>Source transaction</dt><dd>{detail.data.source_txn_id ?? 'Manual score'}</dd>
          <dt>User</dt><dd>{detail.data.user_id}</dd><dt>Time</dt><dd>{formatTimestamp(detail.data.timestamp)}</dd>
          <dt>Amount</dt><dd>{formatAmount(detail.data.amount)}</dd><dt>Merchant category</dt><dd>{detail.data.merchant_category}</dd>
          <dt>Country</dt><dd>{detail.data.country}</dd><dt>Device</dt><dd>{detail.data.device_id}</dd><dt>Channel</dt><dd>{detail.data.channel}</dd>
          <dt>Risk score</dt><dd>{formatScore(detail.data.risk_score)}</dd><dt>Decision</dt><dd>{detail.data.decision}</dd><dt>Risk level</dt><dd><RiskBadge level={detail.data.risk_level} /></dd><dt>Processing sequence</dt><dd>{detail.data.processing_seq}</dd>
          <dt>Alert</dt><dd>{detail.data.alert ? `Alert ${detail.data.alert.alert_id}` : 'None'}</dd>
        </dl>}
      </DetailPanel>}
    </div>
  );
}

export default Dashboard;
