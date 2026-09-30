import { useCallback, useEffect, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

type Stage = 'idle' | 'planning' | 'tool_running' | 'streaming' | 'done' | 'error';
type OllamaState = 'checking' | 'running' | 'stopped' | 'starting';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
const isTauri = () => '__TAURI_INTERNALS__' in window;

export default function App() {
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState<Stage>('idle');
  const [progress, setProgress] = useState('Ready');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPrompt, setLastPrompt] = useState('');
  const [ollama, setOllama] = useState<OllamaState>('checking');
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const expanded = loading || Boolean(content) || Boolean(error);

  const checkOllama = useCallback(async () => {
    if (!isTauri()) return setOllama('stopped');
    try {
      setOllama(await invoke<boolean>('ollama_status') ? 'running' : 'stopped');
    } catch {
      setOllama('stopped');
    }
  }, []);

  useEffect(() => {
    void checkOllama();
    const timer = window.setInterval(() => void checkOllama(), 5000);
    return () => window.clearInterval(timer);
  }, [checkOllama]);

  useEffect(() => {
    if (!isTauri()) return;
    let dispose: (() => void) | undefined;
    void listen('wingent://focus', () => requestAnimationFrame(() => inputRef.current?.focus()))
      .then((unlisten) => { dispose = unlisten; });
    return () => dispose?.();
  }, []);

  useEffect(() => {
    if (isTauri()) void invoke('set_overlay_expanded', { expanded });
  }, [expanded]);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const cancel = () => {
    abortRef.current?.abort();
    setLoading(false);
    setStatus('idle');
    setProgress('Cancelled');
    setError(null);
  };

  const startOllama = async () => {
    if (!isTauri() || ollama === 'starting') return;
    setOllama('starting');
    try {
      await invoke('start_ollama');
      for (let attempt = 0; attempt < 12; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 500));
        if (await invoke<boolean>('ollama_status')) return setOllama('running');
      }
      setOllama('stopped');
      setError('Ollama started but did not become ready. Open Ollama to inspect the error.');
    } catch (cause) {
      setOllama('stopped');
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  };

  const submit = async (value = prompt) => {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    abortRef.current = new AbortController();
    setLastPrompt(trimmed);
    setLoading(true);
    setStatus('planning');
    setProgress('Planning');
    setError(null);
    setContent('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: trimmed }),
        signal: abortRef.current.signal,
      });
      if (!response.ok || !response.body) throw new Error('Wingent service is offline. Start the local backend and try again.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value: chunk } = await reader.read();
        if (done) break;
        buffer += decoder.decode(chunk, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() ?? '';
        for (const event of events) {
          const lines = event.split('\n');
          const name = lines.find((line) => line.startsWith('event:'))?.slice(6).trim();
          const raw = lines.find((line) => line.startsWith('data:'))?.slice(5).trim();
          if (!raw) continue;
          let data: Record<string, string>;
          try { data = JSON.parse(raw) as Record<string, string>; } catch { continue; }
          if (name === 'status') {
            setStatus((data.stage as Stage) ?? 'idle');
            setProgress(data.message ?? 'Working');
          } else if (name === 'delta') {
            setStatus('streaming');
            setContent((current) => current + (data.text ?? ''));
          } else if (name === 'final') {
            setStatus('done');
            setProgress('Complete');
            setContent((current) => current || data.text || current);
          } else if (name === 'error') {
            setStatus('error');
            setProgress('Error');
            setError(data.message ?? 'Something went wrong.');
          }
        }
      }
    } catch (cause) {
      if (!(cause instanceof DOMException && cause.name === 'AbortError')) {
        setStatus('error');
        setProgress('Error');
        setError(cause instanceof Error ? cause.message : 'Unknown error');
      }
    } finally {
      setLoading(false);
    }
  };

  const ollamaLabel = ollama === 'running' ? 'Ollama ready' : ollama === 'starting' ? 'Starting Ollama' : 'Start Ollama';

  return (
    <main className={`overlay ${expanded ? 'overlay-expanded' : ''}`}>
      <section className='command-surface' role='dialog' aria-label='Wingent command bar'>
        <div className='search-row'>
          <div className='wingent-mark' aria-hidden='true'>W</div>
          <label className='sr-only' htmlFor='command-input'>What should Wingent do?</label>
          <input
            id='command-input'
            ref={inputRef}
            aria-label='Command input'
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') void submit();
              if (event.key === 'Escape') {
                event.preventDefault();
                loading ? cancel() : isTauri() && void invoke('hide_overlay');
              }
            }}
            placeholder='Ask Wingent to do anything...'
            autoComplete='off'
            spellCheck='false'
          />
          <button
            type='button'
            className={`ollama-control ollama-${ollama}`}
            onClick={() => ollama !== 'running' && void startOllama()}
            disabled={ollama === 'checking' || ollama === 'starting' || ollama === 'running'}
            aria-label={ollamaLabel}
            title={ollamaLabel}
          >
            <span className='status-dot' />
            {ollama !== 'running' && <span>{ollama === 'starting' ? 'Starting' : 'Start Ollama'}</span>}
          </button>
          <button type='button' className='run-button' onClick={() => void submit()} disabled={loading || !prompt.trim()} aria-label='Run command'>
            {loading ? <span className='spinner' /> : <span aria-hidden='true'>↑</span>}
          </button>
        </div>
        {expanded && (
          <div className='result-panel' aria-live='polite' aria-busy={loading}>
            <div className='result-meta'>
              <span className={`activity-dot activity-${status}`} />
              <span>{progress}</span>
              <div className='result-actions'>
                {loading && <button type='button' onClick={cancel}>Stop</button>}
                {!loading && error && lastPrompt && <button type='button' onClick={() => void submit(lastPrompt)}>Retry</button>}
              </div>
            </div>
            {(content || error) && <div className={`result-copy ${error ? 'result-error' : ''}`}>{error ?? content}</div>}
          </div>
        )}
      </section>
    </main>
  );
}
