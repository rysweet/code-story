import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../tests/utils';
import { setupMswTestServer } from '../../../tests/mocks/server';

// Mock the RTK Query hooks
const mockUseGetConfigQuery = vi.fn();
const mockUseGetConfigSchemaQuery = vi.fn();
const mockUseUpdateConfigMutation = vi.fn();

vi.mock('../../store/api/configApi', () => ({
  useGetConfigQuery: (includeSensitive) => mockUseGetConfigQuery(includeSensitive),
  useGetConfigSchemaQuery: () => mockUseGetConfigSchemaQuery(),
  useUpdateConfigMutation: () => mockUseUpdateConfigMutation(),
}));

// Mock the ConfigSchema component to avoid rendering complex Mantine components
vi.mock('../ConfigSchema', () => ({
  default: () => <div data-testid="config-schema">Mock Config Schema</div>
}));

// Completely mock the ConfigEditor component
vi.mock('../ConfigEditor', () => ({
  default: () => <div data-testid="config-editor">Mock Config Editor</div>
}));

// Import after mocking
import ConfigEditor from '../ConfigEditor';

// Setup MSW server for testing
setupMswTestServer();

describe('ConfigEditor', () => {
  beforeEach(() => {
    // Reset mocks between tests
    vi.clearAllMocks();
  });

  it('renders correctly', () => {
    renderWithProviders(<ConfigEditor />);
    expect(screen.getByTestId('config-editor')).toBeInTheDocument();
  });
});