import React, { useRef, useState } from 'react';
import { ApiError, apiPost, notifyPersistedDataChanged } from '../api/client.js';
import RiskBadge from '../components/RiskBadge.jsx';
import { ErrorState, formatAmount, formatScore, formatTimestamp } from '../components/PageFeedback.jsx';
import '../styles/Page.css';
import '../styles/Analyze.css';
import '../styles/DataStates.css';

const initialForm = { user_id: '', amount: '', merchant_category: '', country: '', channel: '', device_id: '', local_timestamp: '' };

function Analyze() {
  const [formData, setFormData] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [submitted, setSubmitted] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const submittingRef = useRef(false);

  function handleChange(event) {
    setFormData((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (submittingRef.current) return;
    setError(null);
    setResult(null);
    const timestamp = Math.floor(new Date(formData.local_timestamp).getTime() / 1000);
    if (!Number.isFinite(timestamp) || timestamp < 0) {
      setError({ status: 422, message: 'Enter a valid transaction date and time.' });
      return;
    }
    if (!formData.device_id.trim()) {
      setError({ status: 422, message: 'Enter a device ID containing at least one non-space character.' });
      return;
    }
    const body = {
      user_id: Number(formData.user_id),
      timestamp,
      amount: Number(formData.amount),
      device_id: formData.device_id.trim(),
      country: formData.country.trim().toUpperCase(),
      merchant_category: Number(formData.merchant_category),
      channel: Number(formData.channel),
    };
    submittingRef.current = true;
    setLoading(true);
    try {
      const scored = await apiPost('/score', body);
      if (!scored || typeof scored.risk_score !== 'number') throw new ApiError('The scoring API returned no assessment. No result is being displayed.', 500);
      setResult(scored);
      setSubmitted(body);
      notifyPersistedDataChanged();
    } catch (requestError) {
      setError(requestError);
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  }

  return (
    <div className="page-content">
      <h2>Analyze Transaction</h2>
      <p className="subtle">Submit a transaction to the live scoring API. Only the transaction fields are sent; the backend builds the behavioral features.</p>
      <p className="form-note"><span aria-hidden="true">*</span> All fields are required. Merchant category and channel use integer codes.</p>
      <form className="analyze-form" onSubmit={handleSubmit}>
        <div className="form-row"><label htmlFor="user_id">User ID</label><input id="user_id" name="user_id" type="number" step="1" min="0" required value={formData.user_id} onChange={handleChange} /></div>
        <div className="form-row"><label htmlFor="amount">Transaction amount (USD)</label><input id="amount" name="amount" type="number" min="0.01" step="any" required value={formData.amount} onChange={handleChange} /></div>
        <div className="form-row"><label htmlFor="merchant_category">Merchant category</label><input id="merchant_category" name="merchant_category" type="number" step="1" required value={formData.merchant_category} onChange={handleChange} /></div>
        <div className="form-row"><label htmlFor="country">Country code</label><input id="country" name="country" minLength="2" maxLength="2" pattern="[A-Za-z]{2}" title="Enter a two-letter country code, such as US." autoComplete="country" autoCapitalize="characters" required value={formData.country} onChange={handleChange} /><small>Two-letter ISO country code.</small></div>
        <div className="form-row"><label htmlFor="channel">Channel</label><input id="channel" name="channel" type="number" step="1" required value={formData.channel} onChange={handleChange} /></div>
        <div className="form-row"><label htmlFor="device_id">Device ID</label><input id="device_id" name="device_id" required value={formData.device_id} onChange={handleChange} /></div>
        <div className="form-row"><label htmlFor="local_timestamp">Transaction time</label><input id="local_timestamp" name="local_timestamp" type="datetime-local" required value={formData.local_timestamp} onChange={handleChange} /></div>
        <button type="submit" className="primary-button" disabled={loading}>{loading ? 'Scoring transaction…' : 'Analyze Transaction'}</button>
      </form>
      {loading && <p role="status">Waiting for the FraudLens scoring service…</p>}
      {error && <ErrorState error={error} />}
      {result && submitted && <section className="analysis-result" aria-live="polite">
        <h3>Persisted Transaction Assessment</h3>
        <p>Risk score: <strong>{formatScore(result.risk_score)}</strong></p>
        <p>Risk level: <RiskBadge level={result.risk_level} /></p>
        <p>Decision: <strong>{result.decision}</strong></p>
        <h4>Submitted transaction</h4>
        <dl className="detail-list">
          <dt>User ID</dt><dd>{submitted.user_id}</dd><dt>Amount</dt><dd>{formatAmount(submitted.amount)}</dd>
          <dt>Merchant category</dt><dd>{submitted.merchant_category}</dd><dt>Country</dt><dd>{submitted.country}</dd>
          <dt>Channel</dt><dd>{submitted.channel}</dd><dt>Device ID</dt><dd>{submitted.device_id}</dd>
          <dt>Timestamp</dt><dd>{formatTimestamp(submitted.timestamp)}</dd>
        </dl>
        <p className="subtle">The score was accepted by the backend and its persisted-data views have been refreshed.</p>
      </section>}
    </div>
  );
}

export default Analyze;
