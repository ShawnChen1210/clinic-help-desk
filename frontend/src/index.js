import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';
import api from './utils/axiosConfig';

const initializeApp = async () => {
  try {
    const response = await api.get('/api/csrf/');
    const csrfToken = response.data.csrfToken;


    api.defaults.headers.common['X-CSRFToken'] = csrfToken;

    console.log('CSRF token configured successfully!');

  } catch (error) {
    console.error('Failed to fetch CSRF token. POST requests may fail.', error);
  }


  const djangoData = window.djangoData || {
    user: null,
    isAuthenticated: false
  };

  const container = document.getElementById('root');
  const root = createRoot(container);


  root.render(
    <React.StrictMode>
        <App
          initialUser={djangoData.user}
          isAuthenticated={djangoData.isAuthenticated}
        />
    </React.StrictMode>
  );
};

initializeApp();