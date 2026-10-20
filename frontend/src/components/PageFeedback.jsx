import React, { useEffect, useRef } from 'react';

export function LoadingState({ label = 'Loading live data…' }) {
  return <p className="page-state loading-state" role="status"><span className="loading-spinner" aria-hidden="true" />{label}</p>;
}

export function ErrorState({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="page-state page-state-error" role="alert">
      <strong>{error.status ? `Request failed (${error.status})` : 'Backend unavailable'}</strong>
      <p>{error.message}</p>
      {onRetry && <button type="button" className="secondary-button" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function EmptyState({ title = 'No data yet', children }) {
  return (
    <div className="page-state empty-state">
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}

export function Pagination({ page, limit, total, totalPages, onPageChange, onLimitChange }) {
  if (!total) return null;
  return (
    <nav className="pagination" aria-label="Result pages">
      <span>{total} results · page {page} of {Math.max(totalPages, 1)}</span>
      <label>
        Rows per page
        <select value={limit} onChange={(event) => onLimitChange(Number(event.target.value))}>
          {[10, 25, 50, 100].map((size) => <option key={size} value={size}>{size}</option>)}
        </select>
      </label>
      <button type="button" className="secondary-button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
      <button type="button" className="secondary-button" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</button>
    </nav>
  );
}

export function DetailPanel({ title, onClose, loading, error, onRetry, children }) {
  const closeButton = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    const previouslyFocused = document.activeElement;
    closeButton.current?.focus();
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onCloseRef.current();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = closeButton.current?.closest('[role="dialog"]')?.querySelectorAll(
        'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (previouslyFocused instanceof HTMLElement && previouslyFocused.isConnected) previouslyFocused.focus();
    };
  }, []);
  return (
    <div className="detail-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="detail-panel" role="dialog" aria-modal="true" aria-label={title}>
        <div className="detail-heading">
          <h3>{title}</h3>
          <button ref={closeButton} type="button" className="secondary-button" onClick={onClose} aria-label="Close details">Close</button>
        </div>
        {loading && <LoadingState label="Loading details…" />}
        {error && <ErrorState error={error} onRetry={onRetry} />}
        {!loading && !error && children}
      </section>
    </div>
  );
}

export function formatTimestamp(timestamp) {
  if (timestamp === null || timestamp === undefined || timestamp === '') return '—';
  // Convert Unix epoch seconds to Date if appropriate; otherwise show raw value.
  const isEpochSec = Number(timestamp) >= 1e9;
  const date = isEpochSec ? new Date(Number(timestamp) * 1000) : null;
  return isEpochSec && date && !Number.isNaN(date.getTime())
    ? date.toLocaleString()
    : String(timestamp);
}

export function formatAmount(amount) {
  if (amount === null || amount === undefined || !Number.isFinite(Number(amount))) return '—';
  return Number(amount).toLocaleString(undefined, { style: 'currency', currency: 'USD' });
}

export function formatScore(score) {
  return Number.isFinite(Number(score)) ? Number(score).toFixed(3) : '—';
}
