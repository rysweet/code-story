import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBoundary from '../ErrorBoundary';

// Create a component that throws an error
const ErrorComponent = ({ shouldThrow = false }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

// Create a custom fallback component
const CustomFallback = () => <div>Custom fallback component</div>;

// We need to mock console.error to prevent test output noise
const originalConsoleError = console.error;

// Mock Mantine components for the error message
vi.mock('@mantine/core', () => ({
  Alert: ({ title, children, icon }) => (
    <div role="alert" data-title={title}>
      {icon && <span data-testid="icon" />}
      <div>{children}</div>
    </div>
  ),
  Button: ({ children, onClick }) => (
    <button onClick={onClick}>{children}</button>
  ),
  Stack: ({ children }) => <div data-testid="stack">{children}</div>,
  Text: ({ children, size, color }) => (
    <div data-size={size} data-color={color}>{children}</div>
  ),
}));

vi.mock('@tabler/icons-react', () => ({
  IconAlertCircle: () => <span data-testid="alert-icon">Alert Icon</span>
}));

describe('ErrorBoundary', () => {
  // Restore console.error after tests
  beforeEach(() => {
    console.error = vi.fn();
  });

  afterAll(() => {
    console.error = originalConsoleError;
  });

  it('should render children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('should render error message when an error occurs', () => {
    render(
      <ErrorBoundary>
        <ErrorComponent shouldThrow={true} />
      </ErrorBoundary>
    );

    const alert = screen.getByRole('alert');
    expect(alert).toHaveAttribute('data-title', 'Something went wrong');
    expect(screen.getByText('An error occurred while rendering this component.')).toBeInTheDocument();
    expect(screen.getByText('Test error')).toBeInTheDocument();
    expect(screen.getByText('Try again')).toBeInTheDocument();
  });

  it('should render custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<CustomFallback />}>
        <ErrorComponent shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom fallback component')).toBeInTheDocument();
  });

  it('should reset error state when Try Again button is clicked', () => {
    // Spy on setState method
    vi.spyOn(ErrorBoundary.prototype, 'setState');

    render(
      <ErrorBoundary>
        <ErrorComponent shouldThrow={true} />
      </ErrorBoundary>
    );

    const tryAgainButton = screen.getByText('Try again');
    fireEvent.click(tryAgainButton);

    // Check that setState was called to reset the error state
    expect(ErrorBoundary.prototype.setState).toHaveBeenCalledWith({
      hasError: false,
      error: null
    });
  });
});