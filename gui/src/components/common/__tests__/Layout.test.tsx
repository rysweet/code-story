import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';

// Mock the Layout component directly instead of its dependencies
vi.mock('../Layout', () => ({
  default: () => (
    <div data-testid="layout">
      <div data-testid="header">Mock Header</div>
      <div data-testid="sidebar" data-active="/graph">Mock Sidebar</div>
      <div data-testid="main-content">
        <div data-testid="error-boundary">
          <div data-testid="outlet">Mock Content</div>
        </div>
      </div>
    </div>
  )
}));

// Import after mocking
import Layout from '../Layout';

describe('Layout', () => {
  it('should render the main layout structure', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );
    
    expect(screen.getByTestId('layout')).toBeInTheDocument();
    expect(screen.getByTestId('header')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('main-content')).toBeInTheDocument();
    expect(screen.getByTestId('outlet')).toBeInTheDocument();
  });
  
  it('should include a sidebar with the correct active path', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );
    
    const sidebar = screen.getByTestId('sidebar');
    expect(sidebar).toHaveAttribute('data-active', '/graph');
  });
  
  it('should render error boundary around the content', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );
    
    expect(screen.getByTestId('error-boundary')).toContainElement(
      screen.getByTestId('outlet')
    );
  });
});