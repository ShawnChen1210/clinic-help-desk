import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

// Optional: Pass initial Django data to React
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