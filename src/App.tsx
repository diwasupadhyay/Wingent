import { useCallback, useEffect, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

type Stage = 'idle' | 'planning' | 'tool_running' | 'streaming' | 'done' | 'error';
type OllamaState = 'checking' | 'running' | 'stopped' | 'starting';
type StepState = 'pending' | 'running' | 'accepted' | 'failed' | 'not_run';
type ActionStep = { label: string; state: StepState };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
const isTauri = () => '__TAURI_INTERNALS__' in window;

export default function App() {
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState<Stage>('idle');
  const [progress, setProgress] = useState('Ready');
  const [content, setContent] = useState('');
  const [steps, setSteps] = useState<ActionStep[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [lastPrompt, setLastPrompt] = useState('');
  const [ollama, setOllama] = useState<OllamaState>('checking');
  const [backendReady, setBackendReady] = useState<boolean | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const expanded = loading || Boolean(content) || Boolean(error) || backendReady === false;

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
    const checkBackend = async () => {
      try {
        setBackendReady(await invoke<boolean>('backend_status'));
      } catch {
        setBackendReady(false);
      }
    };
    void checkBackend();
    const timer = window.setInterval(() => void checkBackend(), 3000);
    return () => window.clearInterval(timer);
  }, []);

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
    const controller = abortRef.current;
    abortRef.current = null;
    controller?.abort();
    setLoading(false);
    setStatus('idle');
    setProgress('Cancelled');
    setSteps((current) => current.map((step) => step.state === 'pending' || step.state === 'running' ? { ...step, state: 'not_run' } : step));
    setContent('Stopped. Already accepted launch requests cannot be undone; an in-flight launch may still finish.');
    setError(null);
    setErrorCode(null);
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
      setStatus('error');
      setProgress('Ollama unavailable');
    } catch (cause) {
      setOllama('stopped');
      setError(cause instanceof Error ? cause.message : String(cause));
      setStatus('error');
      setProgress('Ollama unavailable');
    }
  };

  const submit = async (value = prompt) => {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setLastPrompt(trimmed);
    setLoading(true);
    setStatus('planning');
    setProgress('Planning');
    setError(null);
    setErrorCode(null);
    setContent('');
    setSteps([]);
    let terminal = false;
    let launchStarted = false;

    try {
      const response = await fetch(`${API_BASE_URL}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: trimmed }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) throw new Error('Wingent service is offline. Start the local backend and try again.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value: chunk } = await reader.read();
        if (abortRef.current !== controller) return;
        if (done) break;
        buffer += decoder.decode(chunk, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() ?? '';
        for (const event of events) {
          const lines = event.split('\n');
          const name = lines.find((line) => line.startsWith('event:'))?.slice(6).trim();
          const raw = lines.find((line) => line.startsWith('data:'))?.slice(5).trim();
          if (!raw) continue;
          let data: { stage?: string; message?: string; text?: string; code?: string; steps?: string[]; index?: number; state?: StepState };
          try { data = JSON.parse(raw); } catch { continue; }
          if (name === 'status') {
            setStatus((data.stage as Stage) ?? 'idle');
            setProgress(data.message ?? 'Working');
          } else if (name === 'plan' && Array.isArray(data.steps)) {
            setSteps(data.steps.map((label) => ({ label, state: 'pending' })));
          } else if (name === 'step') {
            launchStarted = true;
            const index = data.index;
            const state = data.state;
            if (typeof index === 'number' && state) setSteps((current) => current.map((step, i) => i === index ? { ...step, state } : step));
          } else if (name === 'clarification') {
            terminal = true;
            setStatus('done');
            setProgress('Needs your input');
            setContent(data.text ?? 'Please clarify the request.');
          } else if (name === 'delta') {
            setStatus('streaming');
            setContent((current) => current + (data.text ?? ''));
          } else if (name === 'final') {
            terminal = true;
            setStatus('done');
            setProgress('Complete');
            setContent((current) => current || data.text || current);
          } else if (name === 'error') {
            terminal = true;
            setStatus('error');
            setProgress('Error');
            setError(data.message ?? 'Something went wrong.');
            setErrorCode(data.code ?? null);
            setSteps((current) => current.map((step) => step.state === 'pending' ? { ...step, state: 'not_run' } : step));
          }
        }
      }
      if (!terminal) throw new Error('The task connection ended before a result was received. Check any opened windows before trying again.');
    } catch (cause) {
      if (abortRef.current === controller && !(cause instanceof DOMException && cause.name === 'AbortError')) {
        setStatus('error');
        setProgress('Error');
        setError(cause instanceof Error ? cause.message : 'Unknown error');
        if (launchStarted) setErrorCode('partial_execution');
        setSteps((current) => current.map((step) => step.state === 'pending' ? { ...step, state: 'not_run' } : step));
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
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
            placeholder='Ask a question or open an app or site...'
            autoComplete='off'
            spellCheck='false'
          />
          <button
            type='button'
            className={`ollama-control ollama-${ollama}`}
            onClick={() => ollama !== 'running' && void startOllama()}
            disabled={!isTauri() || ollama === 'checking' || ollama === 'starting' || ollama === 'running'}
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
              <span className={`activity-dot activity-${backendReady === false && !loading ? 'error' : status}`} />
              <span>{backendReady === false && !loading && !error ? 'Service unavailable' : progress}</span>
              <div className='result-actions'>
                {loading && <button type='button' onClick={cancel}>Stop</button>}
                {!loading && error && errorCode !== 'partial_execution' && !errorCode?.startsWith('unsupported_') && lastPrompt && (
                  <button type='button' onClick={() => void submit(lastPrompt)}>Retry</button>
                )}
              </div>
            </div>
            {steps.length > 0 && (
              <ol className='action-steps' aria-label='Task steps'>
                {steps.map((step, index) => (
                  <li key={index} className={`step-${step.state}`}>
                    <span className='step-state'>{step.state === 'accepted' ? 'Accepted' : step.state === 'not_run' ? 'Not run' : step.state}</span>
                    <span>{step.label}</span>
                  </li>
                ))}
              </ol>
            )}
            {(content || error || backendReady === false) && (
              <div className={`result-copy ${error || backendReady === false ? 'result-error' : ''}`}>
                {error || content || 'Wingent service is unavailable. Restart Wingent if this persists.'}
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
