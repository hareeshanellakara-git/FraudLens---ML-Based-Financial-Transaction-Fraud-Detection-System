// src/components/TransactionTable.jsx
import React from 'react';
import RiskBadge from './RiskBadge.jsx';
import '../styles/TransactionTable.css';

function TransactionTable({ transactions, onRowClick }) {
  const rows = Array.isArray(transactions) ? transactions : [];
  return (
    <table className="transaction-table">
      <thead>
        <tr>
          <th>Transaction</th>
          <th>Source</th>
          <th>User</th>
          <th>Amount</th>
          <th>Risk Score</th>
          <th>Decision</th>
          <th>Risk</th>
          <th>Time</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(tx => (
          <tr key={tx.transaction_id}>
            <td>{onRowClick ? <button type="button" className="table-link" onClick={() => onRowClick(tx)}>#{tx.transaction_id}</button> : `#${tx.transaction_id}`}</td>
            <td>{tx.source_txn_id ?? 'Manual'}</td>
            <td>{tx.user_id}</td>
            <td>{Number(tx.amount).toLocaleString(undefined, { style: 'currency', currency: 'USD' })}</td>
            <td>{Number(tx.risk_score).toFixed(3)}</td>
            <td>{tx.decision}</td>
            <td><RiskBadge level={tx.risk_level} /></td>
            <td>{Number.isFinite(Number(tx.timestamp)) ? `T+${Math.floor(Number(tx.timestamp) / 3600).toString().padStart(2, '0')}:${Math.floor((Number(tx.timestamp) % 3600) / 60).toString().padStart(2, '0')}:${(Number(tx.timestamp) % 60).toString().padStart(2, '0')}` : tx.timestamp}</td>          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default TransactionTable;
