// src/components/RiskBadge.jsx
import React from 'react';
import '../styles/RiskBadge.css';

function RiskBadge({ level }) {
  const levelUpper = level?.toUpperCase() || '';
  const cls = levelUpper === 'HIGH' ? 'high' : levelUpper === 'MEDIUM' ? 'medium' : levelUpper === 'LOW' ? 'low' : 'unknown';
  return <span className={`risk-badge ${cls}`}>{levelUpper || 'Unavailable'}</span>;
}

export default RiskBadge;
