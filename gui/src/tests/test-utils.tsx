import React, { ReactElement } from 'react';
import { render as rtlRender, RenderOptions } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { vi } from 'vitest';

/**
 * Custom render function that wraps components with necessary providers
 */
const render = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'> & {
    colorScheme?: 'light' | 'dark';
  }
) => {
  const { colorScheme = 'light', ...renderOptions } = options || {};

  // Mock the Mantine hooks used in the components
  vi.mock('@mantine/core', async () => {
    const actual = await vi.importActual('@mantine/core');
    return {
      ...actual,
      useMantineColorScheme: () => ({
        colorScheme,
        toggleColorScheme: vi.fn(),
        setColorScheme: vi.fn(),
      }),
    };
  });

  // Provide the Mantine context
  const Wrapper = ({ children }: { children: React.ReactNode }) => {
    return (
      <MantineProvider
        theme={{ colorScheme }}
        withNormalizeCSS
        withGlobalStyles
      >
        {children}
      </MantineProvider>
    );
  };

  return rtlRender(ui, { wrapper: Wrapper, ...renderOptions });
};

// Re-export everything from testing-library
export * from '@testing-library/react';

// Override render method
export { render };