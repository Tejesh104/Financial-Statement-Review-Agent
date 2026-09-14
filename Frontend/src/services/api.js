import axios from 'axios';

// Resolve the same service origin that the backend uses in the existing
// CHFSRA deployment. Prefer the environment override when present; otherwise
// build the API host from the browser's current server name so LAN and
// localhost testing stay on the real backend port 8001 instead of a stale
// fallback that points to the wrong FastAPI app.
const fallbackBase = (() => {
  const frontendHost = window.location.hostname || 'localhost';
  const protocol = window.location.protocol || 'http:';
  // Standard development and production backend runs on port 8001
  return `${protocol}//${frontendHost}:8001/api/v1`;
})();

let baseApi = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || fallbackBase;
if (typeof window !== 'undefined' && window.location && window.location.hostname && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
  if (baseApi.includes('localhost') || baseApi.includes('127.0.0.1')) {
    baseApi = baseApi.replace('localhost', window.location.hostname).replace('127.0.0.1', window.location.hostname);
  }
}
const API_BASE_URL = baseApi;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000,
});

// Interceptor to attach JWT token from whichever storage bucket the
// existing AuthProvider persisted for the current selected remember-me mode.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('fsra_token') || sessionStorage.getItem('fsra_token');
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return config;
});

export default api;
