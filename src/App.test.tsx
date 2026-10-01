import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
import App from './App';

afterEach(() => vi.unstubAllGlobals());

describe('App', () => {
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
