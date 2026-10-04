import { useCallback, useEffect, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

type Stage = 'idle' | 'planning' | 'observing' | 'verifying' | 'recovering' | 'awaiting_input' | 'unverified' | 'tool_running' | 'streaming' | 'done' | 'error';
type OllamaState = 'checking' | 'running' | 'stopped' | 'starting' | 'missing' | 'unresponsive';
type ModelStatus = { ready: boolean; code: string; message: string; model: string };
type StepState = 'pending' | 'running' | 'accepted' | 'failed' | 'not_run' | 'unknown';
type ActionStep = { label: string; state: StepState };
type Approval = { approval_id: string; token: string; task_id: string; tool: string; arguments: Record<string, unknown>; expires_in: number };
type BackendState = 'ready' | 'incompatible' | 'unavailable';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
const isTauri = () => '__TAURI_INTERNALS__' in window;

export default function App() {
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState<Stage>('idle');
  const [progress, setProgress] = useState('Ready');
  const [content, setContent] = useState('');
  const [steps, setSteps] = useState<ActionStep[]>([]);
  const [reviewActions, setReviewActions] = useState(false);
  const [approval, setApproval] = useState<Approval | null>(null);
  const [approvalBusy, setApprovalBusy] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [lastPrompt, setLastPrompt] = useState('');
  const [resumeTaskId, setResumeTaskId] = useState<string | null>(null);
  const [ollama, setOllama] = useState<OllamaState>('checking');
  const [ollamaMessage, setOllamaMessage] = useState('Checking Ollama');
  const ollamaCheckRef = useRef<Promise<ModelStatus | null> | null>(null);
  const [backendReady, setBackendReady] = useState<BackendState | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const backendProblem = backendReady === 'incompatible'
    ? 'An older or unrelated backend is using port 8000. Quit the old Wingent process, then restart this EXE.'
    : 'Wingent service is unavailable. Restart Wingent if this persists.';
  const expanded = loading || Boolean(content) || Boolean(error) || (backendReady !== null && backendReady !== 'ready');

  const checkOllama = useCallback((): Promise<ModelStatus | null> => {
    if (ollamaCheckRef.current) return ollamaCheckRef.current;
    const request = (async () => {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 6500);
      try {
        const response = await fetch(`${API_BASE_URL}/api/model-status`, { signal: controller.signal });
        if (!response.ok) throw new Error('Model status unavailable');
        const info: ModelStatus = await response.json();
        setOllamaMessage(info.message);
        setOllama((current) => current === 'starting' && !info.ready ? current : info.ready ? 'running'
          : info.code === 'ollama_model_missing' ? 'missing' : info.code === 'ollama_unreachable' ? 'stopped' : 'unresponsive');
        return info;
      } catch {
        setOllamaMessage('Could not check the local model. Retry when the Wingent service is ready.');
        setOllama((current) => current === 'starting' ? current : 'unresponsive');
        return null;
      } finally {
        window.clearTimeout(timeout);
        ollamaCheckRef.current = null;
      }
    })();
    ollamaCheckRef.current = request;
    return request;
  }, []);

  useEffect(() => {
    if (!isTauri()) { setOllama('stopped'); return; }
    if (backendReady !== 'ready') return;
    void checkOllama();
    const timer = window.setInterval(() => void checkOllama(), 8000);
    return () => window.clearInterval(timer);
  }, [checkOllama, backendReady]);

  useEffect(() => {
    if (!isTauri()) return;
    const checkBackend = async () => {
      try {
        setBackendReady(await invoke<BackendState>('backend_status'));
      } catch {
        setBackendReady('unavailable');
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
    setSteps((current) => current.map((step) => step.state === 'running' ? { ...step, state: 'unknown' } : step.state === 'pending' ? { ...step, state: 'not_run' } : step));
    setContent('Stopped. Already accepted actions cannot be undone; an in-flight action may still finish.');
    setError(null);
    setErrorCode(null);
    setApproval(null);
    setApprovalBusy(false);
    setApprovalError(null);
    setResumeTaskId(null);
  };

  const answerApproval = async (approve: boolean) => {
    if (!approval || approvalBusy) return;
    const current = approval;
    const controller = abortRef.current;
    setApprovalBusy(true);
    setApprovalError(null);
    try {
      if (approve && current.tool.startsWith('computer_') && isTauri()) {
        if (current.tool === 'computer_begin' && typeof current.arguments.window_id === 'number') {
          await invoke('handoff_computer_focus', { windowId: current.arguments.window_id });
        } else {
          await invoke('hide_overlay');
        }
      }
      const response = await fetch(`${API_BASE_URL}/api/approvals/${encodeURIComponent(current.approval_id)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: current.token, approve }), signal: controller?.signal,
      });
      if (!response.ok) throw new Error('Approval expired or was already answered. Stop and submit a new request.');
      if (abortRef.current !== controller) return;
      setApproval((pending) => pending?.approval_id === current.approval_id ? null : pending);
    } catch (cause) {
      if (isTauri()) void invoke('reveal_overlay');
      if (abortRef.current === controller) setApprovalError(cause instanceof Error ? cause.message : 'Approval could not be sent.');
    } finally {
      if (abortRef.current === controller) setApprovalBusy(false);
    }
  };

  const startOllama = async () => {
    if (!isTauri() || ollama === 'starting') return;
    if (ollama === 'missing') {
      const info = await checkOllama();
      if (info?.ready) return;
      setError(info?.message ?? ollamaMessage);
      setStatus('error');
      setProgress('Model unavailable');
      return;
    }
    setOllama('starting');
    try {
      await invoke('start_ollama');
      let info: ModelStatus | null = null;
      for (let attempt = 0; attempt < 3; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 500));
        info = await checkOllama();
        if (info?.ready) return setOllama('running');
        if (info?.code === 'ollama_model_missing') break;
      }
      setOllama(info?.code === 'ollama_model_missing' ? 'missing' : 'unresponsive');
      setError(info?.message ?? 'Ollama started but did not become ready. Open Ollama to inspect the error.');
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
    const continuingTask = resumeTaskId;
    const controller = new AbortController();
    abortRef.current = controller;
    setLastPrompt(trimmed);
    setLoading(true);
    setStatus('planning');
    setProgress('Planning');
    setError(null);
    setErrorCode(null);
    setContent('');
    if (!continuingTask) setSteps([]);
    setApproval(null);
    setApprovalError(null);
    setApprovalBusy(false);
    let terminal = false;
    let launchStarted = Boolean(continuingTask);

    try {
      if (isTauri()) {
        const currentBackend = await invoke<BackendState>('backend_status');
        setBackendReady(currentBackend);
        if (currentBackend !== 'ready') {
          throw new Error(currentBackend === 'incompatible'
            ? 'An older or unrelated backend is using port 8000. Quit it and restart this Wingent EXE.'
            : 'Wingent backend is not ready. Restart Wingent and try again.');
        }
      }
      const response = await fetch(`${API_BASE_URL}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: trimmed, review_actions: reviewActions,
          ...(continuingTask ? { resume_task_id: continuingTask } : {}) }),
        signal: controller.signal,
      });
      if (response.status === 409 && continuingTask) {
        setResumeTaskId(null);
        throw new Error('That question expired or was already answered. Start a new task.');
      }
      if (!response.ok || !response.body) {
        let message = 'Wingent service is offline. Start the local backend and try again.';
        try {
          const problem = await response.json();
          if (typeof problem.detail === 'string') message = problem.detail;
        } catch { /* A disconnected service may not return JSON. */ }
        throw new Error(message);
      }
      if (continuingTask) setResumeTaskId(null);

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
          let data: { stage?: string; message?: string; text?: string; code?: string; steps?: string[]; index?: number; state?: StepState; label?: string; outcome?: string; verified?: boolean; resume_task_id?: string } & Partial<Approval>;
          try { data = JSON.parse(raw); } catch { continue; }
          if (name === 'status') {
            setStatus(data.stage === 'executing' ? 'tool_running' : (data.stage as Stage) ?? 'idle');
            setProgress(data.message ?? 'Working');
          } else if (name === 'plan' && Array.isArray(data.steps)) {
            setSteps(data.steps.map((label) => ({ label, state: 'pending' })));
          } else if (name === 'action' && typeof data.index === 'number' && data.label) {
            const index = data.index;
            const label = data.label;
            setSteps((current) => {
              const next = [...current];
              next[index] = { label, state: 'pending' };
              return next;
            });
          } else if (name === 'step') {
            launchStarted = true;
            const index = data.index;
            const state = data.state;
            if (typeof index === 'number' && state) setSteps((current) => current.map((step, i) => i === index ? { ...step, state } : step));
          } else if (name === 'confirmation_required' && data.approval_id && data.token && data.tool && data.arguments) {
            if (isTauri()) void invoke('reveal_overlay');
            setApproval(data as Approval);
            setApprovalBusy(false);
            setApprovalError(null);
            setStatus('awaiting_input');
            setProgress('Waiting for your approval');
          } else if (name === 'clarification') {
            terminal = true;
            setStatus('awaiting_input');
            setProgress('Needs your input');
            setContent(data.text ?? 'Please clarify the request.');
            setResumeTaskId(data.resume_task_id ?? null);
            if (data.resume_task_id) {
              setPrompt('');
              requestAnimationFrame(() => inputRef.current?.focus());
            }
            setSteps((current) => current.map((step) => step.state === 'pending' ? { ...step, state: 'not_run' } : step));
          } else if (name === 'delta') {
            setStatus('streaming');
            setContent((current) => current + (data.text ?? ''));
          } else if (name === 'final') {
            terminal = true;
            setStatus(data.outcome === 'unverified' ? 'unverified' : 'done');
            setProgress(data.outcome === 'unverified' ? 'Result not verified' : data.verified ? 'Goal verified' : 'Response ready');
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
        setSteps((current) => current.map((step) => step.state === 'running' ? { ...step, state: 'unknown' } : step.state === 'pending' ? { ...step, state: 'not_run' } : step));
      }
    } finally {
      if (abortRef.current === controller) {
        if (isTauri()) void invoke('reveal_overlay');
        abortRef.current = null;
        setLoading(false);
        setApproval(null);
        setApprovalBusy(false);
      }
    }
  };

  const ollamaLabel = ollama === 'running' ? 'Ollama ready' : ollama === 'starting' ? 'Starting Ollama'
    : ollama === 'missing' ? 'Check model' : ollama === 'unresponsive' ? 'Retry Ollama'
    : ollama === 'checking' ? 'Checking Ollama' : 'Start Ollama';

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
            placeholder={resumeTaskId ? 'Answer Wingent’s question...' : 'Tell Wingent what you want done...'}
            autoComplete='off'
            spellCheck='false'
          />
          <button type='button' className={`review-toggle ${reviewActions ? 'review-active' : ''}`}
            aria-label='Review actions before running' aria-pressed={reviewActions}
            disabled={loading} onClick={() => setReviewActions((value) => !value)}
            title='Ask before each action, including safe launches'>Review</button>
          <button
            type='button'
            className={`ollama-control ollama-${ollama}`}
            onClick={() => ollama !== 'running' && void startOllama()}
            disabled={!isTauri() || ollama === 'checking' || ollama === 'starting' || ollama === 'running'}
            aria-label={ollamaLabel}
            title={ollamaMessage}
          >
            <span className='status-dot' />
            {ollama !== 'running' && <span>{ollamaLabel}</span>}
          </button>
          <button type='button' className='run-button' onClick={() => void submit()} disabled={loading || !prompt.trim()} aria-label='Run command'>
            {loading ? <span className='spinner' /> : <span aria-hidden='true'>↑</span>}
          </button>
        </div>
        {expanded && (
          <div className='result-panel' aria-live='polite' aria-busy={loading}>
            <div className='result-meta'>
              <span className={`activity-dot activity-${backendReady !== null && backendReady !== 'ready' && !loading ? 'error' : status}`} />
              <span>{backendReady !== null && backendReady !== 'ready' && !loading && !error ? 'Service unavailable' : progress}</span>
              <div className='result-actions'>
                {loading && <button type='button' onClick={cancel}>Stop</button>}
                {!loading && resumeTaskId && <button type='button' onClick={() => {
                  setResumeTaskId(null); setContent(''); setSteps([]); setStatus('idle'); setProgress('Ready');
                }}>New task</button>}
                {!loading && error && errorCode !== 'partial_execution' && !errorCode?.startsWith('unsupported_') && lastPrompt && (
                  <button type='button' onClick={() => void submit(lastPrompt)}>Retry</button>
                )}
              </div>
            </div>
            {approval && (
              <section className='approval-card' aria-label='Action approval'>
                <div>Approve <strong>{approval.tool}</strong>?</div>
                <pre>{JSON.stringify(approval.arguments, null, 2)}</pre>
                <div className='approval-actions'>
                  <button type='button' disabled={approvalBusy} onClick={() => void answerApproval(false)}>Deny</button>
                  <button type='button' disabled={approvalBusy} onClick={() => void answerApproval(true)}>Approve once</button>
                  <span>One action only · expires automatically</span>
                </div>
                {approvalError && <div role='alert'>{approvalError}</div>}
              </section>
            )}
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
            {(content || error || (backendReady !== null && backendReady !== 'ready')) && (
              <div className={`result-copy ${error || (backendReady !== null && backendReady !== 'ready') ? 'result-error' : ''}`}>
                {error || content || backendProblem}
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
