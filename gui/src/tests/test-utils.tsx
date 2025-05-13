import React, { ReactElement } from 'react';
import { render as rtlRender, RenderOptions } from '@testing-library/react';
import { MantineTestProvider } from './MantineTestProvider';
import userEvent from '@testing-library/user-event';

// Extended options for our custom render function
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  colorScheme?: 'light' | 'dark';
  withRouter?: boolean;
  withRedux?: boolean;
  initialRoute?: string;
  preloadedState?: Record<string, any>;
}

/**
 * Custom render function that wraps components with necessary providers
 */
const render = (
  ui: ReactElement,
  options: CustomRenderOptions = {}
) => {
  const {
    colorScheme = 'light',
    withRouter = false,
    withRedux = false,
    initialRoute = '/',
    preloadedState,
    ...renderOptions
  } = options;

  // Set up user event
  const user = userEvent.setup();

  // Provide the Mantine context using our dedicated provider
  const Wrapper = ({ children }: { children: React.ReactNode }) => {
    return (
      <MantineTestProvider
        colorScheme={colorScheme}
        withRouter={withRouter}
        withRedux={withRedux}
        initialRoute={initialRoute}
        preloadedState={preloadedState}
      >
        {children}
      </MantineTestProvider>
    );
  };

  // Render the component with the wrapper
  const result = rtlRender(ui, { wrapper: Wrapper, ...renderOptions });

  // Return the result along with userEvent instance for easier access
  return {
    ...result,
    user,
    // Helper methods for commonly used functionality
    rerender: (ui: ReactElement) => render(ui, options),
  };
};

// Re-export everything from testing-library
export * from '@testing-library/react';

// Override render method
export { render };

// Helper to render a component with full providers - all inclusive setup
export const renderWithProviders = (
  ui: ReactElement,
  options: Omit<CustomRenderOptions, 'withRouter' | 'withRedux'> = {}
) => {
  return render(ui, {
    withRouter: true,
    withRedux: true,
    ...options,
  });
};