import { useEffect, useRef, useState } from 'react';

type Stage = 'idle' | 'planning' | 'tool_running' | 'streaming' | 'done' | 'error';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

export default function App() {
  const [isVisible, setIsVisible] = useState(true);
  const [prompt, setPrompt] = useState('Open Chrome and check my unread emails.');
  const [status, setStatus] = useState<Stage>('idle');
  const [progress, setProgress] = useState('Ready');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSubmittedPrompt, setLastSubmittedPrompt] = useState('');
  const inputRef = useRef<HTMLInputElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.code === 'Space') {
        event.preventDefault();
        setIsVisible((current) => !current);
        requestAnimationFrame(() => inputRef.current?.focus());
      }
      if (event.key === 'Escape') {
        event.preventDefault();
        if (loading) {
          handleCancel();
        } else {
          setIsVisible(false);
        }
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [loading]);

  useEffect(() => {
    if (isVisible) {
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [isVisible]);

  const handleCancel = () => {
    abortRef.current?.abort();
    setLoading(false);
    setStatus('idle');
    setProgress('Cancelled');
    setError('Request cancelled.');
  };

  const handleSubmit = async (submittedPrompt = prompt) => {
    const trimmedPrompt = submittedPrompt.trim();
    if (!trimmedPrompt || loading) return;

    abortRef.current = new AbortController();
    setLastSubmittedPrompt(trimmedPrompt);
    setLoading(true);
    setStatus('planning');
    setProgress('Planning request');
    setError(null);
    setContent('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: trimmedPrompt }),
        signal: abortRef.current.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error('The backend is unavailable. Start the Python agent service first.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split('\n\n');
        buffer = parts.pop() ?? '';

        for (const part of parts) {
          const lines = part.split('\n');
          const eventLine = lines.find((line) => line.startsWith('event:'))?.slice(6).trim();
          const dataLine = lines.find((line) => line.startsWith('data:'))?.slice(5).trim();

          if (!dataLine) continue;

          let data: Record<string, string>;
          try {
            data = JSON.parse(dataLine) as Record<string, string>;
          } catch {
            continue;
          }
          if (eventLine === 'status') {
            setStatus((data.stage as Stage) ?? 'idle');
            setProgress(data.message ?? 'Working');
          }

          if (eventLine === 'delta') {
            setStatus('streaming');
            setContent((current) => current + (data.text ?? ''));
          }

          if (eventLine === 'final') {
            setStatus('done');
            setProgress('Complete');
            setContent((current) => current || data.text || current);
          }

          if (eventLine === 'error') {
            setStatus('error');
            setError(data.message ?? 'Something went wrong.');
            setProgress('Error');
          }
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setStatus('idle');
        setProgress('Cancelled');
        setError('Request cancelled.');
        return;
      }

      setStatus('error');
      setProgress('Error');
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`shell ${isVisible ? 'visible' : 'hidden'}`}>
      <div className="command-bar" role="dialog" aria-modal="false">
        <div className="top-row">
          <div className="brand-wrap">
            <span className="dot" />
            <span>Wingent</span>
          </div>
          <span className="shortcut">Ctrl+Space</span>
        </div>

        <label className="sr-only" htmlFor="command-input">
          Command input
        </label>
        <input
          id="command-input"
          ref={inputRef}
          aria-label="Command input"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              void handleSubmit();
            }
          }}
          placeholder="Ask the agent to open a site, answer a question, or run a task..."
        />

        <div className="meta-row">
          <span className={`status-pill status-${status}`}>{status}</span>
          <span className="progress-text">{progress}</span>
        </div>

        <div className="response-box" aria-live="polite" aria-busy={loading}>
          {content || (error ? error : 'The agent response will appear here.')}
        </div>

        <div className="actions">
          <button type="button" className="secondary" onClick={() => setIsVisible(false)}>
            Close
          </button>
          {loading ? (
            <button type="button" className="secondary" onClick={handleCancel}>
              Cancel
            </button>
          ) : null}
          {!loading && error && lastSubmittedPrompt ? (
            <button type="button" className="secondary" onClick={() => void handleSubmit(lastSubmittedPrompt)}>
              Retry
            </button>
          ) : null}
          <button type="button" className="primary" onClick={() => void handleSubmit()} disabled={loading || !prompt.trim()}>
            {loading ? 'Running…' : 'Run'}
          </button>
        </div>
      </div>
    </div>
  );
}
