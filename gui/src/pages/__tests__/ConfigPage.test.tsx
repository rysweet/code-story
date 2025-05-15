import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../tests/utils';
import { setupMswTestServer } from '../../tests/mocks/server';
import ConfigPage from '../ConfigPage';

// Mock the ConfigEditor component
vi.mock('../../components/config', () => ({
  ConfigEditor: vi.fn(() => <div data-testid="config-editor">Mock ConfigEditor</div>),
}));

// Setup MSW server for testing
setupMswTestServer();

describe('ConfigPage', () => {
  it('renders the config page with title and description', () => {
    renderWithProviders(<ConfigPage />);
    
    // Check page title
    expect(screen.getByText('Configuration')).toBeInTheDocument();
    
    // Check description text
    expect(screen.getByText(/Manage the configuration settings/)).toBeInTheDocument();
    
    // Check ConfigEditor is rendered
    expect(screen.getByTestId('config-editor')).toBeInTheDocument();
  });

  it('sets the active page in Redux on mount', async () => {
    const { store } = renderWithProviders(<ConfigPage />);
    
    // Wait for effect to run
    await waitFor(() => {
      // Check Redux store state
      expect(store.getState().ui.activePage).toBe('config');
    });
  });
});