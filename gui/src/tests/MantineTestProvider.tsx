/**
 * Test provider component for Mantine UI
 * This provides the necessary context for Mantine components in tests
 */
import React, { ReactNode } from 'react';
import { MantineProvider, ColorSchemeProvider } from '@mantine/core';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { rootReducer } from '../store';
import { BrowserRouter } from 'react-router-dom';

// Props for the MantineTestProvider component
interface MantineTestProviderProps {
  children: ReactNode;
  colorScheme?: 'light' | 'dark';
  withRouter?: boolean;
  withRedux?: boolean;
}

/**
 * Test provider that wraps Mantine components with necessary context
 * This ensures they render properly in the test environment with proper theming
 */
export const MantineTestProvider: React.FC<MantineTestProviderProps> = ({
  children,
  colorScheme = 'light',
  withRouter = false,
  withRedux = false,
}) => {
  // Mock toggle function that does nothing
  const toggleColorScheme = () => {};

  // Create store for tests that need Redux
  const store = configureStore({
    reducer: {
      ui: (state = {}, action) => state,
      config: (state = {}, action) => state
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false, // Disable for tests
        immutableCheck: false,    // Disable for tests
      }),
  });

  // Create the base Mantine wrapper - use MantineProvider directly
  const mantineWrapper = (
    <MantineProvider
      withGlobalStyles
      withNormalizeCSS
      theme={{
        colorScheme,
        // Add any theme overrides needed for tests
        primaryColor: 'blue',
        // Other theme properties needed for tests
        components: {
          // Override component styles for testing if needed
        },
      }}
    >
      {children}
    </MantineProvider>
  );

  // Add Router wrapper if requested
  const withRouterWrapper = withRouter
    ? <BrowserRouter>{mantineWrapper}</BrowserRouter>
    : mantineWrapper;

  // Add Redux wrapper if requested
  return withRedux
    ? <Provider store={store}>{withRouterWrapper}</Provider>
    : withRouterWrapper;
};

/**
 * Helper function to wrap components with the MantineTestProvider
 */
export function withMantine(component: React.ReactElement) {
  return <MantineTestProvider>{component}</MantineTestProvider>;
}

/**
 * Helper function to wrap components with full test providers (Mantine, Router, Redux)
 */
export function withAllProviders(component: React.ReactElement) {
  return (
    <MantineTestProvider withRouter withRedux>
      {component}
    </MantineTestProvider>
  );
}