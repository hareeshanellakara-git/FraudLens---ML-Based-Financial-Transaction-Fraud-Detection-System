// src/components/StatCard.jsx
import React from 'react';
import '../styles/StatCard.css';

function StatCard({ title, value }) {
  return (
    <div className="stat-card">
      <div className="stat-title">{title}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

export default StatCard;
