import React, { useEffect, useState } from 'react';
import AlertItem from '../components/AlertItem.jsx';
import RiskBadge from '../components/RiskBadge.jsx';
import useApiData from '../hooks/useApiData.js';
import { DetailPanel, EmptyState, ErrorState, LoadingState, Pagination, formatAmount, formatScore, formatTimestamp } from '../components/PageFeedback.jsx';
import '../styles/Page.css';
import '../styles/Alerts.css';
import '../styles/DataStates.css';

function Alerts() {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('');
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(25);
  const [selectedId, setSelectedId] = useState(null);
  const alerts = useApiData('/alerts', { q: search.trim() || undefined, risk_level: filter || undefined, page, limit });
  const detail = useApiData(selectedId ? `/alerts/${selectedId}` : null, {}, Boolean(selectedId));
  const transaction = detail.data?.transaction;
  const items = Array.isArray(alerts.data?.items) ? alerts.data.items : [];
  const totalPages = alerts.data?.total_pages;

  useEffect(() => {
    if (totalPages !== undefined && page > Math.max(totalPages, 1)) setPage(Math.max(totalPages, 1));
  }, [page, totalPages]);

  return (
    <div className="page-content">
      <h2>Alerts</h2>
      <div className="control-row">
        <label>Search alerts<input type="search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Alert, transaction, or user ID" /></label>
        <label>Risk level<select value={filter} onChange={(event) => { setFilter(event.target.value); setPage(1); }}><option value="">All persisted alerts</option><option value="HIGH">High</option></select></label>
      </div>
      {alerts.loading && !alerts.data && <LoadingState />}
      {alerts.error && <ErrorState error={alerts.error} onRetry={alerts.reload} />}
      {alerts.data && !alerts.error && totalPages !== undefined && page > Math.max(totalPages, 1) && <LoadingState label="Updating to the last available page…" />}
      {alerts.data && !alerts.error && !(totalPages !== undefined && page > Math.max(totalPages, 1)) && (items.length ? <>
        <div className="alerts-list">{items.map((alert) => <AlertItem key={alert.alert_id} alert={alert} onDetails={() => setSelectedId(alert.alert_id)} />)}</div>
        <Pagination page={alerts.data.page} limit={alerts.data.limit} total={alerts.data.total} totalPages={alerts.data.total_pages} onPageChange={setPage} onLimitChange={(value) => { setLimit(value); setPage(1); }} />
      </> : <EmptyState title={search || filter ? 'No matching alerts' : 'No persisted alerts'}>{search || filter ? 'No saved alert matches these filters.' : 'Only persisted HIGH-risk transactions create alerts.'}</EmptyState>)}

      {selectedId !== null && <DetailPanel title={`Alert ${selectedId}`} onClose={() => setSelectedId(null)} loading={detail.loading} error={detail.error} onRetry={detail.reload}>
        {detail.data && <>
          <dl className="detail-list">
            <dt>Alert ID</dt><dd>{detail.data.alert_id}</dd><dt>Transaction ID</dt><dd>{detail.data.transaction_id}</dd>
            <dt>User</dt><dd>{detail.data.user_id}</dd><dt>Timestamp</dt><dd>{formatTimestamp(detail.data.timestamp)}</dd>
            <dt>Risk score</dt><dd>{formatScore(detail.data.risk_score)}</dd><dt>Risk level</dt><dd><RiskBadge level={detail.data.risk_level} /></dd>
          </dl>
          {transaction && <><h4>Associated persisted transaction</h4><dl className="detail-list">
            <dt>Source transaction</dt><dd>{transaction.source_txn_id ?? 'Manual score'}</dd><dt>Amount</dt><dd>{formatAmount(transaction.amount)}</dd>
            <dt>Merchant category</dt><dd>{transaction.merchant_category}</dd><dt>Country</dt><dd>{transaction.country}</dd>
            <dt>Device</dt><dd>{transaction.device_id}</dd><dt>Channel</dt><dd>{transaction.channel}</dd>
            <dt>Decision</dt><dd>{transaction.decision}</dd><dt>Processing sequence</dt><dd>{transaction.processing_seq}</dd>
          </dl></>}
        </>}
      </DetailPanel>}
    </div>
  );
}

export default Alerts;
