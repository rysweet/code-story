import axios from 'axios';

/**
 * Base URL for the Code Story API
 */
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Axios instance configured for the Code Story API
 */
export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Add auth token to requests if available
 */
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Generic error handler for API requests
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle auth errors
      localStorage.removeItem('token');
      // In a real implementation, redirect to login or refresh token
    }
    return Promise.reject(error);
  }
);

/**
 * WebSocket connection for real-time updates
 * @param path - WebSocket path (e.g., '/ws/status/123')
 * @returns WebSocket instance
 */
export const createWebSocket = (path: string): WebSocket => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsBase = API_BASE_URL.replace(/^http(s)?:\/\//, '');
  const wsUrl = `${wsProtocol}//${wsBase}/ws${path}`;
  
  return new WebSocket(wsUrl);
};

/**
 * API endpoints
 */
export const endpoints = {
  health: '/health',
  ingest: {
    start: '/ingest',
    jobs: '/ingest/jobs',
    status: (id: string) => `/ingest/${id}`,
    stop: (id: string) => `/ingest/${id}/stop`,
  },
  query: '/query',
  ask: '/ask',
  config: {
    get: '/config',
    schema: '/config/schema',
    update: '/config',
  },
  service: {
    status: '/service/status',
    start: '/service/start',
    stop: '/service/stop',
  },
  visualize: '/visualize',
};