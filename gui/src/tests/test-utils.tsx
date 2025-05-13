import React, { ReactElement } from 'react';
import { render as rtlRender, RenderOptions } from '@testing-library/react';
import { vi } from 'vitest';
import { MantineTestProvider } from './MantineTestProvider';

/**
 * Custom render function that wraps components with necessary providers
 */
const render = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'> & {
    colorScheme?: 'light' | 'dark';
    withRouter?: boolean;
    withRedux?: boolean;
  }
) => {
  const {
    colorScheme = 'light',
    withRouter = false,
    withRedux = false,
    ...renderOptions
  } = options || {};

  // Provide the Mantine context using our dedicated provider
  const Wrapper = ({ children }: { children: React.ReactNode }) => {
    return (
      <MantineTestProvider
        colorScheme={colorScheme}
        withRouter={withRouter}
        withRedux={withRedux}
      >
        {children}
      </MantineTestProvider>
    );
  };

  return rtlRender(ui, { wrapper: Wrapper, ...renderOptions });
};

// Re-export everything from testing-library
export * from '@testing-library/react';

// Override render method
export { render };