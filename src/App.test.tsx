import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
import App from './App';
import { invoke } from '@tauri-apps/api/core';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn(async (command: string) =>
  command === 'backend_status' ? 'incompatible' :
    command === 'backend_base_url' ? 'http://127.0.0.1:54321' : false) }));
vi.mock('@tauri-apps/api/event', () => ({ listen: vi.fn(async () => () => {}) }));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.mocked(invoke).mockImplementation(async (command: string) =>
    command === 'backend_status' ? 'incompatible' :
      command === 'backend_base_url' ? 'http://127.0.0.1:54321' : false);
});

function mockEvents(events: string) {
  let readCount = 0;
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    body: { getReader: () => ({ read: async () => readCount++ === 0
      ? { done: false, value: new TextEncoder().encode(events) }
      : { done: true } }) },
  })));
}

function runCommand() {
  render(<App />);
  fireEvent.change(screen.getByLabelText(/command input/i), { target: { value: 'my task' } });
  fireEvent.click(screen.getByLabelText(/Run command/i));
}

describe('App', () => {
  it('fills a cloud preset so only a key is needed and sends the chosen provider', async () => {
    const send = vi.fn(async (url: string) => ({ ok: true, json: async () =>
      url.endsWith('/api/provider-presets') ? {
        groq: { label: 'Groq', model: 'vision-default', endpoint: 'https://api.groq.com/openai/v1', note: 'Free plan with limits', key_url: 'https://console.groq.com/keys' },
      } : url.endsWith('/api/settings') ? {
        provider: 'local', service: 'custom', model: 'local-model', endpoint: '', share_screenshots: false, key_configured: false,
      } : { ready: true, model: 'vision-default', message: 'Configured' },
    }));
    vi.stubGlobal('fetch', send);
    render(<App />);
    fireEvent.click(screen.getByLabelText('Settings'));
    await waitFor(() => expect(screen.getByRole('option', { name: 'Groq' })).toBeTruthy());
    fireEvent.change(screen.getByLabelText('Provider'), { target: { value: 'groq' } });
    expect((screen.getByLabelText('Model') as HTMLInputElement).value).toBe('vision-default');
    expect(screen.queryByLabelText('API base URL')).toBeNull();
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'key-test-only' } });
    fireEvent.click(screen.getByText('Save'));
    await waitFor(() => expect(screen.queryByRole('region', { name: 'Model settings' })).toBeNull());
    const saved = vi.mocked(fetch).mock.calls.find(([, options]) => options?.method === 'POST');
    expect(JSON.parse(saved?.[1]?.body as string)).toMatchObject({ provider: 'cloud', service: 'groq', model: 'vision-default', api_key: 'key-test-only' });
    expect(screen.getByLabelText('Cloud model settings')).toBeTruthy();
  });
  it('automatically hands off routine focus without showing an approval card', async () => {
    vi.stubGlobal('__TAURI_INTERNALS__', {});
    vi.mocked(invoke).mockImplementation(async (command: string) => command === 'backend_status' ? 'ready' : command === 'backend_base_url' ? 'http://127.0.0.1:54321' : undefined);
    let reads = 0;
    const send = vi.fn(async (url: string) => {
      if (url.endsWith('/api/model-status')) return { ok: true, json: async () => ({ ready: true, message: 'Ready', model: 'test' }) };
      if (url.includes('/api/approvals/')) return { ok: true };
      return { ok: true, body: { getReader: () => ({ read: async () => {
        const events = [
          'event: confirmation_required\ndata: {"automatic_handoff":true,"approval_id":"focus","token":"test","tool":"computer_begin","arguments":{"window_id":123}}\n\n',
          'event: final\ndata: {"text":"Finished"}\n\n'];
        return reads < events.length ? { done: false, value: new TextEncoder().encode(events[reads++]) } : { done: true };
      } }) } };
    });
    vi.stubGlobal('fetch', send);
    runCommand();
    await waitFor(() => expect(screen.getByText('Finished')).toBeTruthy());
    expect(invoke).toHaveBeenCalledWith('handoff_computer_focus', { windowId: 123 });
    expect(send.mock.calls.some(([url]) => url.includes('/api/approvals/focus'))).toBe(true);
    expect(screen.queryByRole('region', { name: 'Action approval' })).toBeNull();
  });
  it('clears and locks input during a task, then unlocks on Stop', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    runCommand();
    const input = screen.getByLabelText('Command input') as HTMLInputElement;
    expect(input.value).toBe('');
    expect(input.disabled).toBe(true);
    expect(screen.queryByText('W')).toBeNull();
    fireEvent.click(screen.getByText('Stop'));
    expect(input.disabled).toBe(false);
  });
  it('does not show ready for a running server with a missing model', async () => {
    vi.stubGlobal('__TAURI_INTERNALS__', {});
    vi.mocked(invoke).mockImplementation(async (command: string) =>
      command === 'backend_status' ? 'ready' :
        command === 'backend_base_url' ? 'http://127.0.0.1:54321' : false);
    const message = 'Ollama is running, but model "configured:4b" is not installed.';
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({
      ready: false, code: 'ollama_model_missing', model: 'configured:4b', message,
    }) })));
    render(<App />);
    await waitFor(() => expect(screen.getByLabelText('Check model')).toBeTruthy());
    expect(screen.queryByLabelText('Ollama ready')).toBeNull();
    fireEvent.click(screen.getByLabelText('Check model'));
    await waitFor(() => expect(screen.getByText(message)).toBeTruthy());
  });
  it('refuses to submit to an outdated backend in the desktop app', async () => {
    vi.stubGlobal('__TAURI_INTERNALS__', {});
    const send = vi.fn();
    vi.stubGlobal('fetch', send);
    runCommand();
    await waitFor(() => expect(screen.getByText(/wrong backend instance/i)).toBeTruthy());
    expect(send).not.toHaveBeenCalled();
  });
  it('sends desktop commands to the backend port owned by this EXE', async () => {
    vi.stubGlobal('__TAURI_INTERNALS__', {});
    vi.mocked(invoke).mockImplementation(async (command: string) =>
      command === 'backend_status' ? 'ready' :
        command === 'backend_base_url' ? 'http://127.0.0.1:54321' : false);
    const send = vi.fn(async (url: string) => {
      if (url.endsWith('/api/model-status')) return { ok: true, json: async () => ({
        ready: true, code: 'ready', message: 'Model ready', model: 'local',
      }) };
      const bytes = new TextEncoder().encode('event: final\ndata: {"text":"Done"}\n\n');
      let readCount = 0;
      return { ok: true, body: { getReader: () => ({ read: async () => readCount++ === 0
        ? { done: false, value: bytes } : { done: true } }) } };
    });
    vi.stubGlobal('fetch', send);
    runCommand();
    await waitFor(() => expect(screen.getByText('Done')).toBeTruthy());
    expect(send.mock.calls.some(([url]) => url === 'http://127.0.0.1:54321/api/command')).toBe(true);
  });
  it('sends review mode explicitly when enabled', async () => {
    mockEvents('event: final\ndata: {"text":"Ready"}\n\n');
    render(<App />);
    fireEvent.click(screen.getByLabelText('Review actions before running'));
    fireEvent.change(screen.getByLabelText(/command input/i), { target: { value: 'open github' } });
    fireEvent.click(screen.getByLabelText(/Run command/i));
    await waitFor(() => expect(screen.getByText('Ready')).toBeTruthy());
    expect(JSON.parse(vi.mocked(fetch).mock.calls[0][1]?.body as string).review_actions).toBe(true);
  });

  it.each([true, false])('requires an explicit approval response: %s', async (approve) => {
    let readCount = 0;
    let finish: (value: unknown) => void = () => {};
    const waiting = new Promise((resolve) => { finish = resolve; });
    const encode = (text: string) => ({ done: false, value: new TextEncoder().encode(text) });
    const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
      if (url.includes('/api/approvals/')) {
        finish(encode('event: final\ndata: {"outcome":"unverified","text":"Answered"}\n\n'));
        return { ok: true };
      }
      return { ok: true, body: { getReader: () => ({ read: async () => {
        readCount += 1;
        if (readCount === 1) return encode('event: confirmation_required\ndata: {"approval_id":"request1","token":"secret-token","task_id":"task1","tool":"open_url","arguments":{"url":"https://github.com"},"expires_in":60}\n\n');
        if (readCount === 2) return waiting;
        return { done: true };
      } }) } };
    });
    vi.stubGlobal('fetch', fetchMock);
    runCommand();
    await waitFor(() => expect(screen.getByRole('region', { name: 'Action approval' })).toBeTruthy());
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByText('secret-token')).toBeNull();
    fireEvent.click(screen.getByText(approve ? 'Approve once' : 'Deny'));
    await waitFor(() => expect(screen.getByText('Answered')).toBeTruthy());
    expect(JSON.parse(fetchMock.mock.calls[1][1]?.body as string)).toEqual({ token: 'secret-token', approve });
    expect(screen.queryByText('Approve once')).toBeNull();
  });
  it.each([false, true])('handles computer approval handoff failure=%s', async (denyFocus) => {
    vi.stubGlobal('__TAURI_INTERNALS__', {});
    vi.mocked(invoke).mockImplementation(async (command: string) => {
      if (command === 'backend_status') return 'ready';
      if (command === 'backend_base_url') return 'http://127.0.0.1:54321';
      if (command === 'handoff_computer_focus' && denyFocus) throw 'The observed window closed. Observe windows again.';
      return false;
    });
    let readCount = 0;
    let finish: (value: unknown) => void = () => {};
    const waiting = new Promise((resolve) => { finish = resolve; });
    const encode = (text: string) => ({ done: false, value: new TextEncoder().encode(text) });
    const send = vi.fn(async (url: string) => {
      if (url.endsWith('/api/model-status')) return { ok: true, json: async () => ({
        ready: true, code: 'ready', message: 'Model ready', model: 'local',
      }) };
      if (url.includes('/api/approvals/')) {
        finish(encode('event: final\ndata: {"text":"Approved"}\n\n'));
        return { ok: true };
      }
      return { ok: true, body: { getReader: () => ({ read: async () => {
        readCount += 1;
        if (readCount === 1) return encode('event: confirmation_required\ndata: {"approval_id":"request1","token":"secret-token","task_id":"task1","tool":"computer_begin","arguments":{"window_id":722322,"scope":"desktop","purpose":"Inspect window"},"expires_in":60}\n\n');
        if (readCount === 2) return waiting;
        return { done: true };
      } }) } };
    });
    vi.stubGlobal('fetch', send);
    runCommand();
    await waitFor(() => expect(screen.getByRole('region', { name: 'Action approval' })).toBeTruthy());
    expect(screen.getByText(/Across apps and dialogs/)).toBeTruthy();
    fireEvent.click(screen.getByText('Approve once'));
    await waitFor(() => expect(vi.mocked(invoke)).toHaveBeenCalledWith('handoff_computer_focus', { windowId: 722322 }));
    if (denyFocus) {
      await waitFor(() => expect(screen.getByText('The observed window closed. Observe windows again.')).toBeTruthy());
      expect(send.mock.calls.some(([url]) => url.includes('/api/approvals/'))).toBe(false);
    } else {
      await waitFor(() => expect(screen.getByText('Approved')).toBeTruthy());
      expect(send.mock.calls.some(([url]) => url.includes('/api/approvals/'))).toBe(true);
    }
  });
  it('distinguishes launch acceptance from verified completion', async () => {
    mockEvents('event: final\ndata: {"outcome":"unverified","verified":false,"text":"Requests accepted, result not observed."}\n\n');
    runCommand();
    await waitFor(() => expect(screen.getByText('Result not verified')).toBeTruthy());
    expect(screen.queryByText('Goal verified')).toBeNull();
  });

  it('shows verified completion only with explicit evidence status', async () => {
    mockEvents('event: final\ndata: {"outcome":"completed","verified":true,"text":"Evidence checked."}\n\n');
    runCommand();
    await waitFor(() => expect(screen.getByText('Goal verified')).toBeTruthy());
  });

  it('renders changed actions from a recovery plan', async () => {
    mockEvents('event: plan\ndata: {"steps":["Original action"]}\n\n' +
      'event: action\ndata: {"index":0,"label":"Updated action"}\n\n' +
      'event: step\ndata: {"index":0,"state":"accepted"}\n\n' +
      'event: final\ndata: {"outcome":"unverified","text":"Accepted"}\n\n');
    runCommand();
    await waitFor(() => expect(screen.getByText('Updated action')).toBeTruthy());
    expect(screen.queryByText('Original action')).toBeNull();
  });
  it('shows the plan and accepted step results', async () => {
    mockEvents('event: plan\ndata: {"steps":["YouTube search","GitHub tab"]}\n\n' +
      'event: step\ndata: {"index":0,"state":"accepted"}\n\n' +
      'event: step\ndata: {"index":1,"state":"accepted"}\n\n' +
      'event: final\ndata: {"text":"Launch requests accepted."}\n\n');
    runCommand();
    await waitFor(() => expect(screen.getByText('Launch requests accepted.')).toBeTruthy());
    expect(screen.getByText('YouTube search')).toBeTruthy();
    expect(screen.getByText('GitHub tab')).toBeTruthy();
    expect(screen.getAllByText('Accepted')).toHaveLength(2);
  });

  it('asks for clarification instead of claiming completion', async () => {
    mockEvents('event: clarification\ndata: {"text":"Which folder?"}\n\n');
    runCommand();
    await waitFor(() => expect(screen.getByText('Needs your input')).toBeTruthy());
    expect(screen.getByText('Which folder?')).toBeTruthy();
    expect(screen.queryByText('Complete')).toBeNull();
  });

  it('submits an answer using the one-use task continuation', async () => {
    const responses = [
      'event: action\ndata: {"index":0,"label":"First probe"}\n\n' +
      'event: step\ndata: {"index":0,"state":"accepted"}\n\n' +
      'event: clarification\ndata: {"text":"Which option?","resume_task_id":"abc123"}\n\n',
      'event: action\ndata: {"index":1,"label":"Second probe"}\n\n' +
      'event: step\ndata: {"index":1,"state":"accepted"}\n\n' +
      'event: final\ndata: {"outcome":"unverified","text":"Two actions recorded."}\n\n',
    ];
    const fetchMock = vi.fn(async (_url: string, _options?: RequestInit) => {
      const payload = responses.shift() ?? '';
      let reads = 0;
      return { ok: true, body: { getReader: () => ({ read: async () => reads++ === 0
        ? { done: false, value: new TextEncoder().encode(payload) }
        : { done: true } }) } };
    });
    vi.stubGlobal('fetch', fetchMock);
    runCommand();
    await waitFor(() => expect(screen.getByText('Which option?')).toBeTruthy());
    expect(screen.getByPlaceholderText(/Answer Wingent/)).toBeTruthy();
    expect(screen.getByText('New task')).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/command input/i), { target: { value: 'Option B' } });
    fireEvent.click(screen.getByLabelText(/Run command/i));
    await waitFor(() => expect(screen.getByText('Two actions recorded.')).toBeTruthy());
    expect(JSON.parse(fetchMock.mock.calls[1][1]?.body as string)).toMatchObject({
      prompt: 'Option B', resume_task_id: 'abc123',
    });
    expect(screen.getByText('First probe')).toBeTruthy();
    expect(screen.getByText('Second probe')).toBeTruthy();
  });

  it('does not offer whole-task retry after partial execution', async () => {
    mockEvents('event: plan\ndata: {"steps":["First","Second"]}\n\n' +
      'event: step\ndata: {"index":0,"state":"accepted"}\n\n' +
      'event: error\ndata: {"message":"Second failed","code":"partial_execution"}\n\n');
    runCommand();
    await waitFor(() => expect(screen.getByText('Second failed')).toBeTruthy());
    expect(screen.queryByText('Retry')).toBeNull();
    expect(screen.getByText('Not run')).toBeTruthy();
  });

  it('reports a truncated task stream as an error', async () => {
    mockEvents('event: status\ndata: {"stage":"planning","message":"Planning"}\n\n');
    runCommand();
    await waitFor(() => expect(screen.getByText(/connection ended before a result/)).toBeTruthy());
  });
  it('renders the minimal local agent command bar', () => {
    render(<App />);

    expect(screen.getByLabelText(/command input/i)).toBeTruthy();
    expect(screen.getByPlaceholderText(/Tell Wingent/i)).toBeTruthy();
    expect(screen.getByLabelText(/Start Ollama/i)).toBeTruthy();
    expect(screen.getByLabelText(/Run command/i)).toBeTruthy();
  });

  it('shows unsupported tasks without offering a pointless retry', async () => {
    const event = 'event: error\ndata: {"message":"No actions were taken.","code":"unsupported_action"}\n\n';
    const bytes = new TextEncoder().encode(event);
    let readCount = 0;
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: true,
      body: {
        getReader: () => ({
          read: async () => readCount++ === 0
            ? { done: false, value: bytes }
            : { done: true, value: undefined },
        }),
      },
    })));

    render(<App />);
    fireEvent.change(screen.getByLabelText(/command input/i), {
      target: { value: 'Open Chrome and check Gmail' },
    });
    fireEvent.click(screen.getByLabelText(/Run command/i));

    await waitFor(() => expect(screen.getByText('No actions were taken.')).toBeTruthy());
    expect(screen.queryByText('Retry')).toBeNull();
  });
});
