import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock Mantine components for the loading spinner
vi.mock('@mantine/core', () => ({
  Center: ({ children, style }) => (
    <div role="progressbar-container" style={style}>{children}</div>
  ),
  Stack: ({ children, align }) => (
    <div data-align={align}>{children}</div>
  ),
  Loader: () => <div role="progressbar">Loading spinner</div>,
  Text: ({ children, size, color }) => (
    <div data-size={size} data-color={color}>{children}</div>
  ),
}));

// Import after mocking
import LoadingSpinner from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  it('should render with default loading message', () => {
    render(<LoadingSpinner />);

    // Check for the loading spinner
    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    // Check for the default message
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('should render with custom message when provided', () => {
    const customMessage = 'Please wait while data is loading...';
    render(<LoadingSpinner message={customMessage} />);

    // Check for the loading spinner
    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    // Check for the custom message
    expect(screen.getByText(customMessage)).toBeInTheDocument();
  });

  it('should have proper container and styling', () => {
    render(<LoadingSpinner />);

    // Check for the container
    const container = screen.getByRole('progressbar-container');
    expect(container).toBeInTheDocument();

    // Check that elements are properly nested
    expect(container).toContainElement(screen.getByRole('progressbar'));
    expect(container).toContainElement(screen.getByText('Loading...'));
  });
});