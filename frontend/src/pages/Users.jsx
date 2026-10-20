import React, { useEffect, useState } from 'react';
import UserCard from '../components/UserCard.jsx';
import useApiData from '../hooks/useApiData.js';
import TransactionTable from '../components/TransactionTable.jsx';
import { DetailPanel, EmptyState, ErrorState, LoadingState, Pagination, formatAmount, formatScore, formatTimestamp } from '../components/PageFeedback.jsx';
import '../styles/Page.css';
import '../styles/Users.css';
import '../styles/DataStates.css';

function Users() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(25);
  const [selectedId, setSelectedId] = useState(null);
  const users = useApiData('/users', { q: search.trim() || undefined, page, limit });
  const detail = useApiData(selectedId !== null ? `/users/${selectedId}` : null, {}, selectedId !== null);
  const items = Array.isArray(users.data?.items) ? users.data.items : [];
  const totalPages = users.data?.total_pages;

  useEffect(() => {
    if (totalPages !== undefined && page > Math.max(totalPages, 1)) setPage(Math.max(totalPages, 1));
  }, [page, totalPages]);

  return (
    <div className="page-content">
      <h2>Users</h2>
      <div className="control-row"><label>Search users<input type="search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="User ID" /></label></div>
      {users.loading && !users.data && <LoadingState />}
      {users.error && <ErrorState error={users.error} onRetry={users.reload} />}
      {users.data && !users.error && totalPages !== undefined && page > Math.max(totalPages, 1) && <LoadingState label="Updating to the last available page…" />}
      {users.data && !users.error && !(totalPages !== undefined && page > Math.max(totalPages, 1)) && (items.length ? <>
        <div className="users-grid">{items.map((user) => <UserCard key={user.user_id} user={user} onDetails={() => setSelectedId(user.user_id)} />)}</div>
        <Pagination page={users.data.page} limit={users.data.limit} total={users.data.total} totalPages={users.data.total_pages} onPageChange={setPage} onLimitChange={(value) => { setLimit(value); setPage(1); }} />
      </> : <EmptyState title={search ? 'No matching users' : 'No persisted users yet'}>{search ? 'Try a different user ID.' : 'Users appear after one of their transactions is scored and persisted.'}</EmptyState>)}

      {selectedId !== null && <DetailPanel title={`User ${selectedId}`} onClose={() => setSelectedId(null)} loading={detail.loading} error={detail.error} onRetry={detail.reload}>
        {detail.data && <>
          <dl className="detail-list">
            <dt>Transactions</dt><dd>{detail.data.transaction_count}</dd><dt>Average amount</dt><dd>{formatAmount(detail.data.average_amount)}</dd>
            <dt>Latest timestamp</dt><dd>{formatTimestamp(detail.data.latest_timestamp)}</dd><dt>Latest risk score</dt><dd>{formatScore(detail.data.latest_risk_score)}</dd>
            <dt>High-risk count</dt><dd>{detail.data.high_risk_count}</dd><dt>Known devices</dt><dd>{detail.data.known_device_count}</dd><dt>Known countries</dt><dd>{detail.data.known_country_count}</dd>
            <p className="note">Counts reflect persisted transactions only and may lag behind real‑time state.</p>
          </dl>
          <h4>Recent persisted transactions</h4>
          {detail.data.recent_transactions?.length ? <div className="table-wrap"><TransactionTable transactions={detail.data.recent_transactions} /></div> : <EmptyState title="No recent transactions returned" />}
        </>}
      </DetailPanel>}
    </div>
  );
}

export default Users;
