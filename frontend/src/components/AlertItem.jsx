import React from 'react';
import RiskBadge from './RiskBadge.jsx';
import '../styles/AlertItem.css';
import { formatScore, formatTimestamp } from './PageFeedback.jsx';

function AlertItem({ alert, onDetails }) {
  return (
    <article className="alert-item">
      <RiskBadge level={alert.risk_level} />
      <div className="alert-copy">
        <strong>Alert {alert.alert_id} · Transaction {alert.transaction_id}</strong>
        <div className="details">User {alert.user_id} · Risk {formatScore(alert.risk_score)} · {formatTimestamp(alert.timestamp)}</div>
      </div>
      <button type="button" className="secondary-button" onClick={onDetails}>View details</button>
    </article>
  );
}

export default AlertItem;
