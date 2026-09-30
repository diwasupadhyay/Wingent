import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders the minimal local agent command bar', () => {
    render(<App />);

    expect(screen.getByLabelText(/command input/i)).toBeTruthy();
    expect(screen.getByPlaceholderText(/Ask Wingent/i)).toBeTruthy();
    expect(screen.getByLabelText(/Start Ollama/i)).toBeTruthy();
    expect(screen.getByLabelText(/Run command/i)).toBeTruthy();
  });
});
