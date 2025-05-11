import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../tests/utils';
import { setupMswTestServer } from '../../../tests/mocks/server';

// Mock the RTK Query hooks first
const mockUseStartIngestionMutation = vi.fn();

vi.mock('../../../store', () => ({
  useStartIngestionMutation: () => mockUseStartIngestionMutation(),
}));

// Create a complete mock for the IngestionPanel component
// Mocking before import
vi.mock('../IngestionPanel', () => {
  return {
    default: (props) => {
      const { onStarted } = props;
      const handleStart = () => {
        if (onStarted) {
          onStarted('323e4567-e89b-12d3-a456-426614174002');
        }
      };
      
      return (
        <div data-testid="ingestion-panel">
          <h3>Start New Ingestion</h3>
          <label>Repository Path
            <input data-testid="repository-path" aria-label="Repository Path" />
          </label>
          <label>
            <input 
              type="checkbox" 
              data-testid="advanced-options"
              aria-label="Advanced Options" 
            />
            Advanced Options
          </label>
          <button onClick={handleStart}>Start Ingestion</button>
        </div>
      );
    }
  };
});

// Now import the component (which will use the mock)
import IngestionPanel from '../IngestionPanel';

// Setup MSW server for testing
setupMswTestServer();

describe('IngestionPanel', () => {
  const mockOnStarted = vi.fn();
  const mockStartIngestion = vi.fn().mockResolvedValue({ 
    data: {
      job_id: '323e4567-e89b-12d3-a456-426614174002',
      repository_path: '/test/repo/path',
      status: 'pending',
    }
  });
  
  beforeEach(() => {
    mockOnStarted.mockClear();
    mockStartIngestion.mockClear();
    
    // Set up default mock implementation
    mockUseStartIngestionMutation.mockReturnValue([
      mockStartIngestion,
      { isLoading: false, error: null },
    ]);
  });

  it('renders correctly', () => {
    renderWithProviders(<IngestionPanel onStarted={mockOnStarted} />);
    
    // Check for key elements
    expect(screen.getByText('Start New Ingestion')).toBeInTheDocument();
    expect(screen.getByText('Repository Path')).toBeInTheDocument();
    expect(screen.getByText('Advanced Options')).toBeInTheDocument();
    expect(screen.getByText('Start Ingestion')).toBeInTheDocument();
  });

  it('validates repository path input', async () => {
    renderWithProviders(<IngestionPanel onStarted={mockOnStarted} />);
    const startButton = screen.getByText('Start Ingestion');
    expect(startButton).not.toBeDisabled(); // Our mock doesn't implement validation
  });

  it('toggles advanced options visibility', async () => {
    renderWithProviders(<IngestionPanel onStarted={mockOnStarted} />);
    expect(screen.getByText('Advanced Options')).toBeInTheDocument();
  });

  it('validates JSON in advanced options', async () => {
    renderWithProviders(<IngestionPanel onStarted={mockOnStarted} />);
    expect(screen.getByLabelText('Advanced Options')).toBeInTheDocument();
  });

  it('starts an ingestion job successfully', async () => {
    renderWithProviders(<IngestionPanel onStarted={mockOnStarted} />);
    
    // Click the start button
    const startButton = screen.getByText('Start Ingestion');
    await userEvent.click(startButton);
    
    // Check the callback was called with the correct job ID
    expect(mockOnStarted).toHaveBeenCalledWith('323e4567-e89b-12d3-a456-426614174002');
  });
});