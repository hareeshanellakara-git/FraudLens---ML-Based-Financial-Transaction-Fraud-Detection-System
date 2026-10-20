import React, { useEffect, useState } from 'react';
import TransactionTable from '../components/TransactionTable.jsx';
import useApiData from '../hooks/useApiData.js';
import { DetailPanel, EmptyState, ErrorState, LoadingState, Pagination, formatAmount, formatScore, formatTimestamp } from '../components/PageFeedback.jsx';
import RiskBadge from '../components/RiskBadge.jsx';
import '../styles/Page.css';
import '../styles/Transactions.css';
import '../styles/DataStates.css';

function Transactions() {
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [decision, setDecision] = useState('');
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(25);
  const [selectedId, setSelectedId] = useState(null);
  const query = { q: search.trim() || undefined, risk_level: riskFilter || undefined, decision: decision || undefined, page, limit };
  const transactions = useApiData('/transactions', query);
  const detail = useApiData(selectedId ? `/transactions/${selectedId}` : null, {}, Boolean(selectedId));
  const items = Array.isArray(transactions.data?.items) ? transactions.data.items : [];
  const totalPages = transactions.data?.total_pages;

  useEffect(() => {
    if (totalPages !== undefined && page > Math.max(totalPages, 1)) setPage(Math.max(totalPages, 1));
  }, [page, totalPages]);

  function updateSearch(setter, value) { setter(value); setPage(1); }

  return (
    <div className="page-content">
      <h2>Transactions</h2>
      <div className="control-row">
        <label>Search<input type="search" value={search} onChange={(event) => updateSearch(setSearch, event.target.value)} placeholder="Transaction, source, user, or device" /></label>
        <label>Risk level<select value={riskFilter} onChange={(event) => updateSearch(setRiskFilter, event.target.value)}><option value="">All levels</option><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option></select></label>
        <label>Decision<select value={decision} onChange={(event) => updateSearch(setDecision, event.target.value)}><option value="">All decisions</option><option value="fraud">Fraud</option><option value="legitimate">Legitimate</option></select></label>
      </div>
      {transactions.loading && !transactions.data && <LoadingState />}
      {transactions.error && <ErrorState error={transactions.error} onRetry={transactions.reload} />}
      {transactions.data && !transactions.error && totalPages !== undefined && page > Math.max(totalPages, 1) && <LoadingState label="Updating to the last available page…" />}
      {transactions.data && !transactions.error && !(totalPages !== undefined && page > Math.max(totalPages, 1)) && (items.length ? <>
        {transactions.loading && <LoadingState label="Refreshing transactions…" />}
        <div className="table-wrap"><TransactionTable transactions={items} onRowClick={(tx) => setSelectedId(tx.transaction_id)} /></div>
        <Pagination page={transactions.data.page} limit={transactions.data.limit} total={transactions.data.total} totalPages={transactions.data.total_pages} onPageChange={setPage} onLimitChange={(value) => { setLimit(value); setPage(1); }} />
      </> : <EmptyState title={search || riskFilter || decision ? 'No matching transactions' : 'No transactions yet'}>{search || riskFilter || decision ? 'Try changing or clearing the filters.' : 'Scored transactions will appear here after they are persisted.'}</EmptyState>)}

      {selectedId !== null && <DetailPanel title={`Transaction ${selectedId}`} onClose={() => setSelectedId(null)} loading={detail.loading} error={detail.error} onRetry={detail.reload}>
        {detail.data && <dl className="detail-list">
          <dt>Source transaction</dt><dd>{detail.data.source_txn_id ?? 'Manual score'}</dd><dt>User</dt><dd>{detail.data.user_id}</dd>
          <dt>Timestamp</dt><dd>{formatTimestamp(detail.data.timestamp)}</dd><dt>Amount</dt><dd>{formatAmount(detail.data.amount)}</dd>
          <dt>Merchant category</dt><dd>{detail.data.merchant_category}</dd><dt>Country</dt><dd>{detail.data.country}</dd>
          <dt>Device</dt><dd>{detail.data.device_id}</dd><dt>Channel</dt><dd>{detail.data.channel}</dd>
          <dt>Risk score</dt><dd>{formatScore(detail.data.risk_score)}</dd><dt>Risk level</dt><dd><RiskBadge level={detail.data.risk_level} /></dd>
          <dt>Decision</dt><dd>{detail.data.decision}</dd><dt>Processing sequence</dt><dd>{detail.data.processing_seq}</dd>
          <dt>Alert</dt><dd>{detail.data.alert ? `Alert ${detail.data.alert.alert_id}` : 'None'}</dd>
        </dl>}
      </DetailPanel>}
    </div>
  );
}

export default Transactions;
