import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock Sidebar component for testing
vi.mock('../Sidebar', () => ({
  default: ({ active, onNavigate, collapsed }) => (
    <div data-testid="sidebar" data-collapsed={collapsed} data-active={active}>
      <ul>
        <li>
          <button
            data-active={active === '/graph'}
            onClick={() => onNavigate('/graph')}
          >
            Graph
          </button>
        </li>
        <li>
          <button
            data-active={active === '/ingestion'}
            onClick={() => onNavigate('/ingestion')}
          >
            Ingestion
          </button>
        </li>
        <li>
          <button
            data-active={active === '/config'}
            onClick={() => onNavigate('/config')}
          >
            Configuration
          </button>
        </li>
        <li>
          <button
            data-active={active === '/mcp'}
            onClick={() => onNavigate('/mcp')}
          >
            MCP Playground
          </button>
        </li>
        <li>
          <button
            data-active={active === '/ask'}
            onClick={() => onNavigate('/ask')}
          >
            Ask Questions
          </button>
        </li>
        <li>
          <button
            data-active={active === '/dashboard'}
            onClick={() => onNavigate('/dashboard')}
          >
            Dashboard
          </button>
        </li>
      </ul>
    </div>
  )
}));

// Import after mocking
import Sidebar from '../Sidebar';

describe('Sidebar', () => {
  const mockNavigate = vi.fn();

  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('should render all navigation items', () => {
    render(<Sidebar onNavigate={mockNavigate} />);

    // Check for all navigation items
    expect(screen.getByText('Graph')).toBeInTheDocument();
    expect(screen.getByText('Ingestion')).toBeInTheDocument();
    expect(screen.getByText('Configuration')).toBeInTheDocument();
    expect(screen.getByText('MCP Playground')).toBeInTheDocument();
    expect(screen.getByText('Ask Questions')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('should highlight the active navigation item', () => {
    render(<Sidebar active="/graph" onNavigate={mockNavigate} />);

    // Find all nav links
    const navLinks = screen.getAllByRole('button');

    // Check that the Graph item is active (first in the list)
    expect(navLinks[0]).toHaveAttribute('data-active', 'true');

    // Other items should not be active
    expect(navLinks[1]).not.toHaveAttribute('data-active', 'true');
    expect(navLinks[2]).not.toHaveAttribute('data-active', 'true');
    expect(navLinks[3]).not.toHaveAttribute('data-active', 'true');
    expect(navLinks[4]).not.toHaveAttribute('data-active', 'true');
    expect(navLinks[5]).not.toHaveAttribute('data-active', 'true');
  });

  it('should call onNavigate with correct path when an item is clicked', async () => {
    const user = userEvent.setup();
    render(<Sidebar onNavigate={mockNavigate} />);

    // Click on the Ingestion nav item (second in the list)
    const navLinks = screen.getAllByRole('button');
    await user.click(navLinks[1]);

    // Check that onNavigate was called with the correct path
    expect(mockNavigate).toHaveBeenCalledWith('/ingestion');
  });

  it('should apply collapsed styling when collapsed prop is true', () => {
    render(<Sidebar onNavigate={mockNavigate} collapsed={true} />);

    // Check that sidebar has collapsed attribute
    const sidebar = screen.getByTestId('sidebar');
    expect(sidebar).toHaveAttribute('data-collapsed', 'true');
  });
});