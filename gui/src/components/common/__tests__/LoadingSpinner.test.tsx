import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React, { ReactNode } from 'react';
import { vi } from 'vitest';
import { MantineProvider } from '@mantine/core';

// Mock Mantine components for the loading spinner
vi.mock('@mantine/core', () => ({
  Center: ({ children, style }: { children: ReactNode; style?: React.CSSProperties }) => (
    <div data-testid="center" style={style}>{children}</div>
  ),
  Stack: ({ children, align, spacing }: { children: ReactNode; align?: string; spacing?: string }) => (
    <div data-testid="stack" data-align={align} data-spacing={spacing}>{children}</div>
  ),
  Loader: ({ size }: { size?: string }) => (
    <div data-testid="loader" data-size={size}>Loading spinner</div>
  ),
  Text: ({ children, size, color }: { children: ReactNode; size?: string; color?: string }) => (
    <div data-testid="text" data-size={size} data-color={color}>{children}</div>
  ),
  MantineProvider: ({ children }: any) => <div>{children}</div>
}));

// Import after mocking
import LoadingSpinner from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  it('should render with default loading message', () => {
    render(
      <MantineProvider>
        <LoadingSpinner />
      </MantineProvider>
    );

    // Check for the loading spinner
    expect(screen.getByTestId('loader')).toBeInTheDocument();

    // Check for the default message
    expect(screen.getByTestId('text')).toHaveTextContent('Loading...');
  });

  it('should render with custom message when provided', () => {
    const customMessage = 'Please wait while data is loading...';
    render(
      <MantineProvider>
        <LoadingSpinner message={customMessage} />
      </MantineProvider>
    );

    // Check for the loading spinner
    expect(screen.getByTestId('loader')).toBeInTheDocument();

    // Check for the custom message
    expect(screen.getByTestId('text')).toHaveTextContent(customMessage);
  });

  it('should have proper container and styling', () => {
    render(
      <MantineProvider>
        <LoadingSpinner />
      </MantineProvider>
    );

    // Check for the container
    const center = screen.getByTestId('center');
    expect(center).toBeInTheDocument();

    // Center element should contain a min height style
    expect(center.style).toHaveProperty('minHeight', '200px');
    expect(center.style).toHaveProperty('height', '100%');

    // Check that the loader has the correct size
    expect(screen.getByTestId('loader')).toHaveAttribute('data-size', 'md');

    // Check that the stack has centered alignment
    expect(screen.getByTestId('stack')).toHaveAttribute('data-align', 'center');

    // Check that the text has the correct styling
    const text = screen.getByTestId('text');
    expect(text).toHaveAttribute('data-size', 'sm');
    expect(text).toHaveAttribute('data-color', 'dimmed');
  });
});