import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
import App from './App';

afterEach(() => vi.unstubAllGlobals());

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
