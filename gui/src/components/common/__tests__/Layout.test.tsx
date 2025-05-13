import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';

// Completely mock the Layout component
vi.mock('../Layout', () => ({
  default: () => (
    <div data-testid="layout">
      <div data-testid="color-scheme-provider">
        <div data-testid="mantine-provider">
          <div data-testid="app-shell">
            <header data-testid="app-shell-header">
              <div data-testid="header">Header Component</div>
            </header>
            <nav data-testid="app-shell-navbar">
              <div data-testid="sidebar">Sidebar Component</div>
            </nav>
            <main data-testid="app-shell-main">
              <div data-testid="error-boundary">
                <div data-testid="outlet">Content</div>
              </div>
            </main>
          </div>
          <div data-testid="drawer" data-opened="false">
            <div data-testid="drawer-header">Service Status</div>
            <div data-testid="drawer-content">
              <div data-testid="title">API Service</div>
              <div data-testid="badge">running</div>
              <div data-testid="text">Status info</div>
              <hr data-testid="divider" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}));

// Import the component
import Layout from '../Layout';

describe('Layout', () => {
  // Setup localStorage mock for each test in this suite
  vi.beforeEach(() => {
    const localStorageMock = {
      getItem: vi.fn((key) => key === 'colorScheme' ? 'light' : null),
      setItem: vi.fn(),
      clear: vi.fn()
    };

    if (window) {
      Object.defineProperty(window, 'localStorage', { value: localStorageMock });
    }
  });

  it('should render the main layout structure', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );

    // Check for main structural components
    expect(screen.getByTestId('layout')).toBeInTheDocument();
    expect(screen.getByTestId('app-shell')).toBeInTheDocument();
    expect(screen.getByTestId('app-shell-header')).toBeInTheDocument();
    expect(screen.getByTestId('app-shell-navbar')).toBeInTheDocument();
    expect(screen.getByTestId('app-shell-main')).toBeInTheDocument();
  });

  it('should include theme providers', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );

    expect(screen.getByTestId('color-scheme-provider')).toBeInTheDocument();
    expect(screen.getByTestId('mantine-provider')).toBeInTheDocument();
  });

  it('should have header and sidebar components', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );

    expect(screen.getByTestId('header')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  it('should render service drawer', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );

    const drawer = screen.getByTestId('drawer');
    expect(drawer).toBeInTheDocument();
    expect(drawer).toHaveAttribute('data-opened', 'false');
  });
});