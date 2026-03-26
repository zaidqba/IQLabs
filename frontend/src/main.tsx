import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { loadStoredTokens } from './services/api';

// Restore auth tokens from localStorage before first render
loadStoredTokens();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
