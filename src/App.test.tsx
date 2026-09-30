import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders the local agent command bar', () => {
    render(<App />);

    expect(screen.getByText(/Wingent/i)).toBeTruthy();
    expect(screen.getByLabelText(/command input/i)).toBeTruthy();
  });
});
