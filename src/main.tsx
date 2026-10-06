import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';
import { invoke } from '@tauri-apps/api/core';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {new URLSearchParams(window.location.search).has('task-toast') ?
      <button className='task-toast' onClick={() => void invoke('reveal_overlay')}>
        <span className='status-dot' /> Wingent is working <small>View task · Stop</small>
      </button> : <App />}
  </React.StrictMode>,
);
