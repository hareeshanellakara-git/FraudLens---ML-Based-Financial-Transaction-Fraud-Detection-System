const configuredBase = import.meta.env.VITE_API_BASE_URL || '/api';
const API_BASE = configuredBase.replace(/\/$/, '');
const DATA_CHANGED_EVENT = 'fraudlens:data-changed';

export class ApiError extends Error {
  constructor(message, status = null, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

function errorMessage(status, detail) {
  if (status === 400) return 'Please check the request and try again.';
  if (status === 404) return 'The requested record was not found.';
  if (status === 409) return 'This transaction has already been processed.';
  if (status === 422) return 'Please check the transaction details and try again.';
  if (status >= 500) return 'Something went wrong while processing the request.';
  return `The request could not be completed (HTTP ${status}).`;
}

export async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError('Unable to connect to FraudLens API. Check the connection and try again.');
  }

  if (response.status === 204) return null;

  let payload = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const detail = payload?.detail;
    throw new ApiError(errorMessage(response.status, detail), response.status, detail);
  }
  if (payload === null) throw new ApiError('The server returned an unreadable response.', response.status);
  return payload;
}

export function apiGet(path, query = {}, options = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  });
  const suffix = params.size ? `?${params.toString()}` : '';
  return apiRequest(`${path}${suffix}`, options);
}

export function apiPost(path, body) {
  return apiRequest(path, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function notifyPersistedDataChanged() {
  window.dispatchEvent(new CustomEvent(DATA_CHANGED_EVENT));
}

export { API_BASE };
