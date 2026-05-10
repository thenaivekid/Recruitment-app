import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '';

const client = axios.create({ baseURL: BASE_URL });

// Attach JWT token on every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect to login on 401
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const login = (email, password) =>
  client.post('/auth/login', { email, password });

export const register = (email, password) =>
  client.post('/auth/register', { email, password });

// ── Candidates ────────────────────────────────────────────────────────────────
export const getCandidates = (params) =>
  client.get('/candidates', { params });

export const getCandidate = (id) =>
  client.get(`/candidates/${id}`);

export const createCandidate = (data) =>
  client.post('/candidates', data);

export const updateCandidate = (id, data) =>
  client.patch(`/candidates/${id}`, data);

export const submitScore = (id, data) =>
  client.post(`/candidates/${id}/scores`, data);

export const generateSummary = (id) =>
  client.post(`/candidates/${id}/summary`);

export default client;
