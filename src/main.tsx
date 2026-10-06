import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';
import { invoke } from '@tauri-apps/api/core';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {new URLSearchParams(window.location.search).has('task-toast') ?
      <button className='task-toast' onClick={() => void invoke('reveal_overlay')}>
        <span className='task-orbit' aria-hidden='true' />
        <span className='task-toast-copy'>Working on your task<small>Wingent · View progress or stop</small></span>
        <span className='task-toast-arrow' aria-hidden='true'>↗</span>
      </button> : <App />}
  </React.StrictMode>,
);
