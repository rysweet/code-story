import { describe, it, expect, vi, beforeEach, afterAll } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React, { ReactNode } from 'react';
import { MantineProvider } from '@mantine/core';
import ErrorBoundary from '../ErrorBoundary';

interface ErrorComponentProps {
  shouldThrow?: boolean;
}

// Create a component that throws an error
const ErrorComponent: React.FC<ErrorComponentProps> = ({ shouldThrow = false }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

// Create a custom fallback component
const CustomFallback: React.FC = () => <div>Custom fallback component</div>;

// We need to mock console.error to prevent test output noise
const originalConsoleError = console.error;

// Mock Mantine components for the error message
vi.mock('@mantine/core', () => ({
  Alert: ({ title, children, icon, color, variant }: { title: string; children: ReactNode; icon?: ReactNode; color?: string; variant?: string }) => (
    <div data-testid="alert" data-title={title} data-color={color} data-variant={variant}>
      {icon && <span data-testid="alert-icon" />}
      <div>{children}</div>
    </div>
  ),
  Button: ({ children, onClick, variant, color }: { children: ReactNode; onClick?: () => void; variant?: string; color?: string }) => (
    <button
      data-testid="button"
      data-variant={variant}
      data-color={color}
      onClick={onClick}
    >
      {children}
    </button>
  ),
  Stack: ({ children, spacing }: { children: ReactNode; spacing?: string }) => (
    <div data-testid="stack" data-spacing={spacing}>{children}</div>
  ),
  Text: ({ children, size, color }: { children: ReactNode; size?: string; color?: string }) => (
    <div data-testid="text" data-size={size} data-color={color}>{children}</div>
  ),
  MantineProvider: ({ children }: any) => <div>{children}</div>
}));

vi.mock('@tabler/icons-react', () => ({
  IconAlertCircle: ({ size }: { size?: number }) => (
    <span data-testid="icon-alert-circle" data-size={size}>Alert Icon</span>
  )
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
      <MantineProvider>
        <ErrorBoundary>
          <div>Test content</div>
        </ErrorBoundary>
      </MantineProvider>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('should render error message when an error occurs', () => {
    render(
      <MantineProvider>
        <ErrorBoundary>
          <ErrorComponent shouldThrow={true} />
        </ErrorBoundary>
      </MantineProvider>
    );

    const alert = screen.getByTestId('alert');
    expect(alert).toHaveAttribute('data-title', 'Something went wrong');
    expect(alert).toHaveAttribute('data-color', 'red');
    expect(alert).toHaveAttribute('data-variant', 'filled');

    expect(screen.getByTestId('alert-icon')).toBeInTheDocument();

    // Get all text elements and check their contents
    const textElements = screen.getAllByTestId('text');
    const errorElement = textElements.find(el =>
      el.textContent === 'An error occurred while rendering this component.'
    );
    expect(errorElement).toBeInTheDocument();

    // Error message should be displayed
    const errorMessages = screen.getAllByTestId('text');
    const errorMessageElement = errorMessages.find(el => el.textContent === 'Test error');
    expect(errorMessageElement).toBeDefined();
    expect(errorMessageElement).toBeInTheDocument();

    // Try again button should be displayed
    expect(screen.getByTestId('button')).toHaveTextContent('Try again');
  });

  it('should render custom fallback when provided', () => {
    render(
      <MantineProvider>
        <ErrorBoundary fallback={<CustomFallback />}>
          <ErrorComponent shouldThrow={true} />
        </ErrorBoundary>
      </MantineProvider>
    );

    expect(screen.getByText('Custom fallback component')).toBeInTheDocument();
  });

  it('should reset error state when Try Again button is clicked', () => {
    // Spy on setState method
    vi.spyOn(ErrorBoundary.prototype, 'setState');

    render(
      <MantineProvider>
        <ErrorBoundary>
          <ErrorComponent shouldThrow={true} />
        </ErrorBoundary>
      </MantineProvider>
    );

    const tryAgainButton = screen.getByText('Try again');
    fireEvent.click(tryAgainButton);

    // Check that setState was called to reset the error state
    expect(ErrorBoundary.prototype.setState).toHaveBeenCalledWith({
      hasError: false,
      error: null
    });
  });

  it('should log error in componentDidCatch', () => {
    const errorSpy = vi.spyOn(console, 'error');

    render(
      <MantineProvider>
        <ErrorBoundary>
          <ErrorComponent shouldThrow={true} />
        </ErrorBoundary>
      </MantineProvider>
    );

    // Console.error should have been called with the error
    expect(errorSpy).toHaveBeenCalled();
  });
});