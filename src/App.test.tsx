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
  it('distinguishes launch acceptance from verified completion', async () => {
    mockEvents('event: final\ndata: {"outcome":"unverified","verified":false,"text":"Requests accepted, result not observed."}\n\n');
    runCommand();
    await waitFor(() => expect(screen.getByText('Requests sent · not verified')).toBeTruthy());
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
    expect(screen.getByPlaceholderText(/Ask a question/i)).toBeTruthy();
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
