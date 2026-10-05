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
type CloudService = 'custom' | 'groq' | 'google' | 'openai' | 'anthropic';
type ProviderSettings = { provider: 'local' | 'cloud'; service: CloudService; model: string; endpoint: string; api_key: string; share_screenshots: boolean };
type ProviderPreset = { label: string; endpoint: string; model: string; note: string; key_url: string };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
const isTauri = () => '__TAURI_INTERNALS__' in window;

export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsBusy, setSettingsBusy] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState('');
  const [provider, setProvider] = useState<'local' | 'cloud'>('local');
  const [activeService, setActiveService] = useState<CloudService>('custom');
  const [activeModel, setActiveModel] = useState('qwen3-vl:4b-instruct');
  const [settings, setSettings] = useState<ProviderSettings>({ provider: 'local', service: 'custom', model: 'qwen3-vl:4b-instruct', endpoint: '', api_key: '', share_screenshots: false });
  const [presets, setPresets] = useState<Partial<Record<CloudService, ProviderPreset>>>({});
  const [keyConfigured, setKeyConfigured] = useState(false);
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
  const apiBaseUrlRef = useRef(API_BASE_URL);
  const backendProblem = backendReady === 'incompatible'
    ? 'Wingent connected to the wrong backend instance. Restart this EXE.'
    : 'Wingent service is unavailable. Restart Wingent if this persists.';
  const expanded = settingsOpen || loading || Boolean(content) || Boolean(error) || (backendReady !== null && backendReady !== 'ready');

  const openSettings = async () => {
    if (loading) return;
    setSettingsMessage('');
    setSettingsOpen(true);
    try {
      if (isTauri()) apiBaseUrlRef.current = await invoke<string>('backend_base_url');
      const [response, catalogue] = await Promise.all([
        fetch(`${apiBaseUrlRef.current}/api/settings`), fetch(`${apiBaseUrlRef.current}/api/provider-presets`),
      ]);
      if (!response.ok || !catalogue.ok) throw new Error('Settings unavailable');
      const info = await response.json();
      setPresets(await catalogue.json());
      setKeyConfigured(info.key_configured);
      setSettings({ provider: info.provider, service: info.service ?? 'custom', model: info.model, endpoint: info.endpoint, api_key: '', share_screenshots: info.share_screenshots });
      setProvider(info.provider);
      setActiveService(info.service ?? 'custom');
      setActiveModel(info.model);
    } catch { setSettingsMessage('Could not load settings. Check the Wingent service.'); }
  };

  const chooseProvider = (choice: string) => {
    setKeyConfigured(false);
    setSettingsMessage('');
    const service = choice as CloudService;
    const preset = presets[service];
    setSettings({ provider: choice === 'local' ? 'local' : 'cloud', service: choice === 'local' ? 'custom' : service,
      model: choice === 'local' ? 'qwen3-vl:4b-instruct' : preset?.model ?? '',
      endpoint: preset?.endpoint ?? '', api_key: '', share_screenshots: false });
  };

  const openKeyPage = async () => {
    const preset = presets[settings.service];
    if (!preset) return;
    try {
      if (isTauri()) await invoke('open_provider_key_page', { service: settings.service });
      else window.open(preset.key_url, '_blank', 'noopener,noreferrer');
    } catch { setSettingsMessage('Could not open the provider page. Visit its API console in your browser.'); }
  };

  const saveSettings = async () => {
    setSettingsBusy(true);
    setSettingsMessage('');
    try {
      const response = await fetch(`${apiBaseUrlRef.current}/api/settings`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings),
      });
      if (!response.ok) throw new Error('Check the model, HTTPS endpoint and API key.');
      setProvider(settings.provider);
      setActiveService(settings.service);
      setActiveModel(settings.model);
      setKeyConfigured(settings.provider === 'cloud');
      setSettings((current) => ({ ...current, api_key: '' }));
      setSettingsOpen(false);
      void checkOllama();
    } catch (cause) { setSettingsMessage(cause instanceof Error ? cause.message : 'Could not save settings.'); }
    finally { setSettingsBusy(false); }
  };

  const checkOllama = useCallback((): Promise<ModelStatus | null> => {
    if (ollamaCheckRef.current) return ollamaCheckRef.current;
    const request = (async () => {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 6500);
      try {
        const response = await fetch(`${apiBaseUrlRef.current}/api/model-status`, { signal: controller.signal });
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
        apiBaseUrlRef.current = await invoke<string>('backend_base_url');
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
    if (isTauri()) void invoke('set_overlay_expanded', { expanded, settings: settingsOpen });
  }, [expanded, settingsOpen]);

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
      const response = await fetch(`${apiBaseUrlRef.current}/api/approvals/${encodeURIComponent(current.approval_id)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: current.token, approve }), signal: controller?.signal,
      });
      if (!response.ok) throw new Error('Approval expired or was already answered. Stop and submit a new request.');
      if (abortRef.current !== controller) return;
      setApproval((pending) => pending?.approval_id === current.approval_id ? null : pending);
    } catch (cause) {
      if (isTauri()) void invoke('reveal_overlay');
      if (abortRef.current === controller) setApprovalError(
        typeof cause === 'string' ? cause : cause instanceof Error ? cause.message : 'Approval could not be sent.');
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
    if (!trimmed || loading || abortRef.current || settingsOpen) return;
    const continuingTask = resumeTaskId;
    const controller = new AbortController();
    abortRef.current = controller;
    setLastPrompt(trimmed);
    setPrompt('');
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
        apiBaseUrlRef.current = await invoke<string>('backend_base_url');
        const currentBackend = await invoke<BackendState>('backend_status');
        setBackendReady(currentBackend);
        if (currentBackend !== 'ready') {
          throw new Error(currentBackend === 'incompatible'
            ? 'Wingent connected to the wrong backend instance. Restart this Wingent EXE.'
            : 'Wingent backend is not ready. Restart Wingent and try again.');
        }
      }
      if (isTauri()) await invoke('hide_overlay');
      const response = await fetch(`${apiBaseUrlRef.current}/api/command`, {
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
          let data: { stage?: string; message?: string; text?: string; code?: string; steps?: string[]; index?: number; state?: StepState; label?: string; outcome?: string; verified?: boolean; resume_task_id?: string; automatic_handoff?: boolean } & Partial<Approval>;
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
            if (data.automatic_handoff === true && data.tool === 'computer_begin' && isTauri() && typeof data.arguments.window_id === 'number') {
              setProgress('Focusing the requested application');
              await invoke('handoff_computer_focus', { windowId: data.arguments.window_id });
              if (abortRef.current !== controller) return;
              const handoff = await fetch(`${apiBaseUrlRef.current}/api/approvals/${encodeURIComponent(data.approval_id)}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: data.token, approve: true }), signal: controller.signal,
              });
              if (!handoff.ok) throw new Error('Application focus handoff expired. Stop and retry the task.');
              continue;
            }
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
          <label className='sr-only' htmlFor='command-input'>What should Wingent do?</label>
          <input
            id='command-input'
            ref={inputRef}
            aria-label='Command input'
            value={prompt}
            disabled={loading}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') void submit();
              if (event.key === 'Escape') {
                event.preventDefault();
                loading ? cancel() : isTauri() && void invoke('hide_overlay');
              }
            }}
            placeholder={loading ? 'Working on your task…' : resumeTaskId ? 'Answer Wingent’s question...' : 'Tell Wingent what you want done...'}
            autoComplete='off'
            spellCheck='false'
          />
          <button type='button' className='settings-button' aria-label='Settings' title='Model settings'
            disabled={loading || settingsBusy} onClick={() => settingsOpen ? setSettingsOpen(false) : void openSettings()}>
            <svg width='19' height='19' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='1.5' aria-hidden='true'><path d='m9 3-.6 2.2-1.8 1L4.4 6 2 10l1.7 1.6v1.8L2 15l2.4 4 2.2-.2 1.8 1L9 22h5l.6-2.2 1.8-1 2.2.2 2.4-4-1.7-1.6v-1.8L21 10l-2.4-4-2.2.2-1.8-1L14 3Z'/><circle cx='11.5' cy='12.5' r='3.1'/></svg>
          </button>
          <button type='button' className={`review-toggle ${reviewActions ? 'review-active' : ''}`}
            aria-label='Review actions before running' aria-pressed={reviewActions}
            disabled={loading} onClick={() => setReviewActions((value) => !value)}
            title='Ask before each action, including safe launches'>Review</button>
          <button
            type='button'
            className={`ollama-control ollama-${ollama} ${provider === 'cloud' ? 'provider-cloud' : ''}`}
            onClick={() => provider === 'cloud' ? void openSettings() : ollama !== 'running' && void startOllama()}
            disabled={loading || (provider !== 'cloud' && (!isTauri() || ollama === 'checking' || ollama === 'starting' || ollama === 'running'))}
            aria-label={provider === 'cloud' ? 'Cloud model settings' : ollamaLabel}
            title={provider === 'cloud' ? `Cloud: ${activeModel}` : ollamaMessage}
          >
            <span className='status-dot' />
            {provider === 'cloud' ? <span>{presets[activeService]?.label ?? 'Cloud'}</span> : ollama !== 'running' && <span>{ollamaLabel}</span>}
          </button>
          <button type='button' className='run-button' onClick={() => void submit()} disabled={loading || settingsOpen || !prompt.trim()} aria-label='Run command'>
            {loading ? <span className='spinner' /> : <span aria-hidden='true'>↑</span>}
          </button>
        </div>
        {settingsOpen && (
          <section className='settings-panel' aria-label='Model settings'>
            <div className='settings-heading'><div><h2>Make it yours</h2><p>Choose the brain behind your assistant.</p></div><span className='session-badge'>This session</span></div>
            <fieldset disabled={settingsBusy}>
            <div className='settings-grid'>
              <label>Provider<select value={settings.provider === 'local' ? 'local' : settings.service} onChange={(e) => chooseProvider(e.target.value)}>
                <option value='local'>On this PC · Ollama</option>
                {Object.entries(presets).map(([id, preset]) => <option key={id} value={id}>{preset.label}</option>)}
                <option value='custom'>Custom compatible API</option>
              </select></label>
              <label>Model<input value={settings.model} placeholder='Vision-capable model ID' onChange={(e) => setSettings({ ...settings, model: e.target.value })} /></label>
              {settings.provider === 'cloud' && <>
                {settings.service === 'custom' && <label>API base URL<input value={settings.endpoint} placeholder='https://your-provider.example/v1' onChange={(e) => { setKeyConfigured(false); setSettings({ ...settings, endpoint: e.target.value }); }} /></label>}
                <label className={settings.service === 'custom' ? '' : 'settings-wide'}>API key<input type='password' autoComplete='off' value={settings.api_key} placeholder={keyConfigured ? 'Saved for this session · leave blank to keep' : 'Paste your API key'} onChange={(e) => setSettings({ ...settings, api_key: e.target.value })} /></label>
              </>}
            </div>
            {settings.provider === 'cloud' && presets[settings.service] && <div className='provider-note'><span>{presets[settings.service]?.note}</span><button type='button' onClick={() => void openKeyPage()}>Get API key ↗</button></div>}
            {settings.provider === 'cloud' && <label className='cloud-consent'><input type='checkbox' checked={settings.share_screenshots} onChange={(e) => setSettings({ ...settings, share_screenshots: e.target.checked })} />Send screenshots to this provider for vision. Task text and tool results also leave this PC.</label>}
            </fieldset>
            <div className='settings-footer'><span role={settingsMessage ? 'alert' : undefined}>{settingsMessage || (settings.provider === 'local' ? 'Local inference. Your API key is never needed.' : 'Keys stay in memory until you quit Wingent.')}</span>
              <button disabled={settingsBusy || !settings.model.trim()} onClick={() => void saveSettings()}>{settingsBusy ? 'Saving…' : 'Save'}</button></div>
          </section>
        )}
        {expanded && !settingsOpen && (
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
                  <span>{approval.tool === 'computer_begin'
                    ? (approval.arguments.scope === 'desktop'
                      ? 'Across apps and dialogs · until this task ends · Stop revokes control'
                      : 'This window · until this task ends · Stop revokes control')
                    : 'One action only · expires automatically'}</span>
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
