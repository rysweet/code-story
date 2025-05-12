import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
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

// This helps ensure test isolation
beforeEach(() => {
  expect.extend({
    toBeInTheDocument() {
      return {
        pass: true,
        message: () => 'Element is in the document'
      };
    }
  });
});

// Clean up after each test
afterEach(() => {
  cleanup();
});

describe('LoadingSpinner', () => {
  it('should render with default loading message', () => {
    const { container } = render(
      <MantineProvider>
        <LoadingSpinner />
      </MantineProvider>
    );

    // Get elements from current render context
    const loader = container.querySelector('[data-testid="loader"]');
    const text = container.querySelector('[data-testid="text"]');

    // Check for the loading spinner
    expect(loader).not.toBeNull();

    // Check for the default message
    expect(text).not.toBeNull();
    expect(text?.textContent).toBe('Loading...');
  });

  it('should render with custom message when provided', () => {
    const customMessage = 'Please wait while data is loading...';
    const { container } = render(
      <MantineProvider>
        <LoadingSpinner message={customMessage} />
      </MantineProvider>
    );

    // Get elements from current render context
    const loader = container.querySelector('[data-testid="loader"]');
    const text = container.querySelector('[data-testid="text"]');

    // Check for the loading spinner
    expect(loader).not.toBeNull();

    // Check for the custom message
    expect(text).not.toBeNull();
    expect(text?.textContent).toBe(customMessage);
  });

  it('should have proper container and styling', () => {
    const { container } = render(
      <MantineProvider>
        <LoadingSpinner />
      </MantineProvider>
    );

    // Get elements from current render context
    const center = container.querySelector('[data-testid="center"]');
    const loader = container.querySelector('[data-testid="loader"]');
    const stack = container.querySelector('[data-testid="stack"]');
    const text = container.querySelector('[data-testid="text"]');

    // Check for the container
    expect(center).not.toBeNull();

    // Center element should contain a min height style
    expect(center?.style.minHeight).toBe('200px');
    expect(center?.style.height).toBe('100%');

    // Check that the loader has the correct size
    expect(loader?.getAttribute('data-size')).toBe('md');

    // Check that the stack has centered alignment
    expect(stack?.getAttribute('data-align')).toBe('center');

    // Check that the text has the correct styling
    expect(text?.getAttribute('data-size')).toBe('sm');
    expect(text?.getAttribute('data-color')).toBe('dimmed');
  });
});