// src/components/UserCard.jsx
import React from 'react';
import '../styles/UserCard.css';

function UserCard({ user, onDetails }) {
  return (
    <div className="user-card">
      <h3>User {user.user_id}</h3>
      <p>Persisted transactions: {user.transaction_count}</p>
      <p>Average amount: {Number(user.average_amount).toLocaleString(undefined, { style: 'currency', currency: 'USD' })}</p>
      <p>High-risk transactions: {user.high_risk_count}</p>
      <p>Known devices: {user.known_device_count}</p>
      <p>Known countries: {user.known_country_count}</p>
      <p>Latest risk score: {Number(user.latest_risk_score).toFixed(3)}</p>
      <button type="button" className="secondary-button" onClick={onDetails}>View user details</button>
    </div>
  );
}

export default UserCard;
