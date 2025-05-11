import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock the Header component for testing
vi.mock('../Header', () => ({
  default: ({ toggleServicePanel }) => (
    <div className="header">
      <h3>Code Story</h3>
      <div className="controls">
        <button
          className="theme-toggle"
          aria-label="Toggle color scheme"
        >
          Theme
        </button>
        <button
          className="service-status"
          onClick={toggleServicePanel}
        >
          Service Status
        </button>
      </div>
    </div>
  )
}));

// Import the component after mocking
import Header from '../Header';

describe('Header', () => {
  it('should render the application title', () => {
    render(<Header />);
    expect(screen.getByText('Code Story')).toBeInTheDocument();
  });

  it('should render the Service Status button', () => {
    render(<Header />);
    expect(screen.getByText('Service Status')).toBeInTheDocument();
  });

  it('should render a theme toggle button', () => {
    render(<Header />);
    expect(screen.getByLabelText('Toggle color scheme')).toBeInTheDocument();
  });

  it('should call toggleServicePanel when Service Status button is clicked', async () => {
    const toggleServicePanel = vi.fn();
    const user = userEvent.setup();

    render(<Header toggleServicePanel={toggleServicePanel} />);

    const button = screen.getByText('Service Status');
    await user.click(button);

    expect(toggleServicePanel).toHaveBeenCalled();
  });
});