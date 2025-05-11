import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../tests/utils';
import { setupMswTestServer } from '../../tests/mocks/server';
import IngestionPage from '../IngestionPage';

// Create a mock for Mantine Collapse component
vi.mock('@mantine/core', async () => {
  const actual = await vi.importActual('@mantine/core');
  return {
    ...actual,
    Collapse: ({ in: visible, children }) => (
      visible ? children : null
    ),
  };
});

// Mock the component imports to simplify testing of integration
vi.mock('../../components/ingest', () => ({
  IngestionPanel: vi.fn(({ onStarted }) => (
    <div data-testid="ingestion-panel">
      <button onClick={() => onStarted('test-job-id')}>Mock Start Ingestion</button>
    </div>
  )),
  JobsList: vi.fn(({ onViewDetails }) => (
    <div data-testid="jobs-list">
      <button onClick={() => onViewDetails('test-job-id')}>Mock View Details</button>
    </div>
  )),
  ProgressTracker: vi.fn(({ jobId, onClose }) => (
    <div data-testid="progress-tracker">
      Job ID: {jobId}
      <button onClick={onClose}>Mock Close</button>
    </div>
  )),
}));

// Setup MSW server for testing
setupMswTestServer();

describe('IngestionPage', () => {
  beforeEach(() => {
    // Clear any Redux action history between tests
    vi.clearAllMocks();
  });

  it('renders the page with initial components', () => {
    renderWithProviders(<IngestionPage />);
    
    // Check for page title
    expect(screen.getByText('Ingestion Dashboard')).toBeInTheDocument();
    
    // Check for main components
    expect(screen.getByTestId('ingestion-panel')).toBeInTheDocument();
    expect(screen.getByTestId('jobs-list')).toBeInTheDocument();
    
    // Progress tracker should not be visible initially
    expect(screen.queryByTestId('progress-tracker')).not.toBeInTheDocument();
  });

  it('toggles new ingestion panel visibility', async () => {
    const user = userEvent.setup();
    renderWithProviders(<IngestionPage />);
    
    // Check that panel is visible initially
    expect(screen.getByTestId('ingestion-panel')).toBeInTheDocument();
    
    // Click the hide button
    const toggleButton = screen.getByText('Hide New Ingestion');
    await user.click(toggleButton);
    
    // Check that panel is no longer visible
    expect(screen.queryByTestId('ingestion-panel')).not.toBeInTheDocument();
    
    // Check that button text changed
    expect(screen.getByText('Show New Ingestion')).toBeInTheDocument();
    
    // Click the show button
    await user.click(screen.getByText('Show New Ingestion'));
    
    // Check that panel is visible again
    expect(screen.getByTestId('ingestion-panel')).toBeInTheDocument();
  });

  it('shows progress tracker when job is started', async () => {
    const user = userEvent.setup();
    renderWithProviders(<IngestionPage />);
    
    // Start a job
    const startButton = screen.getByText('Mock Start Ingestion');
    await user.click(startButton);
    
    // Progress tracker should now be visible
    expect(screen.getByTestId('progress-tracker')).toBeInTheDocument();
    expect(screen.getByText('Job ID: test-job-id')).toBeInTheDocument();
  });

  it('shows progress tracker when job details are viewed', async () => {
    const user = userEvent.setup();
    renderWithProviders(<IngestionPage />);
    
    // View job details
    const viewButton = screen.getByText('Mock View Details');
    await user.click(viewButton);
    
    // Progress tracker should now be visible
    expect(screen.getByTestId('progress-tracker')).toBeInTheDocument();
    expect(screen.getByText('Job ID: test-job-id')).toBeInTheDocument();
    
    // The new ingestion panel should be hidden
    expect(screen.queryByTestId('ingestion-panel')).not.toBeInTheDocument();
  });

  it('hides progress tracker when closed', async () => {
    const user = userEvent.setup();
    renderWithProviders(<IngestionPage />);
    
    // View job details to show the tracker
    const viewButton = screen.getByText('Mock View Details');
    await user.click(viewButton);
    
    // Progress tracker should be visible
    expect(screen.getByTestId('progress-tracker')).toBeInTheDocument();
    
    // Close the tracker
    const closeButton = screen.getByText('Mock Close');
    await user.click(closeButton);
    
    // Progress tracker should no longer be visible
    expect(screen.queryByTestId('progress-tracker')).not.toBeInTheDocument();
  });

  it('sets the active page in Redux on mount', async () => {
    const { store } = renderWithProviders(<IngestionPage />);
    
    // Wait for effect to run
    await waitFor(() => {
      // Check Redux store state
      expect(store.getState().ui.activePage).toBe('ingest');
    });
  });
});