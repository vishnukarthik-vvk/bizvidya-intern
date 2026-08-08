// src/api.js
// Central API client. Place this file at: src/api.js
//
// SETUP: add this line to your .env file:
//   REACT_APP_API_URL=https://bizvidya-intern.onrender.com

export const API_BASE = (
  process.env.REACT_APP_API_URL || 'http://localhost:8000'
).replace(/\/$/, '');

const TOKEN_KEY = 'access_token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);

export const setSession = ({ access_token, user_id, email, role }) => {
  if (access_token) localStorage.setItem(TOKEN_KEY, access_token);
  if (user_id !== undefined) localStorage.setItem('user_id', String(user_id));
  if (email) localStorage.setItem('user_email', email);
  if (role) localStorage.setItem('user_role', role);
};

export const clearSession = () => {
  [TOKEN_KEY, 'user_id', 'user_email', 'user_role'].forEach(k =>
    localStorage.removeItem(k)
  );
};

export const getRole = () => localStorage.getItem('user_role') || 'student';

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (networkError) {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }

  if (res.status === 401) {
    clearSession();
    if (!window.location.pathname.startsWith('/login')) {
      window.location.assign('/login');
    }
    throw new ApiError(401, 'Your session expired. Please log in again.');
  }

  const text = await res.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = { detail: text }; }
  }

  if (!res.ok) {
    const detail =
      (data && (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))) ||
      `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return data;
}

export const get  = (path, opts) => api(path, { ...opts, method: 'GET' });
export const post = (path, body, opts) => api(path, { ...opts, method: 'POST', body });
export const del  = (path, opts) => api(path, { ...opts, method: 'DELETE' });

// Trailing-edge debounce used to prevent one DB write per second/keystroke.
export function debounce(fn, waitMs = 2000) {
  let timer = null;
  const wrapped = (...args) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { timer = null; fn(...args); }, waitMs);
  };
  wrapped.flush = (...args) => {
    if (timer) clearTimeout(timer);
    timer = null;
    fn(...args);
  };
  wrapped.cancel = () => {
    if (timer) clearTimeout(timer);
    timer = null;
  };
  return wrapped;
}
