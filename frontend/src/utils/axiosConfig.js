import axios from 'axios';

const api = axios.create({
  baseURL: '/',  // Same domain as Django
  withCredentials: true,  // Send cookies (sessionid, csrftoken)
});

// Add CSRF token to requests
api.interceptors.request.use((config) => {
  const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1];
  if (csrfToken) config.headers['X-CSRFToken'] = csrfToken;
  return config;
});

export default api;