/**
 * Test provider component for Mantine UI
 * This provides the necessary context for Mantine components in tests
 */
import React, { ReactNode } from 'react';
import { MantineProvider } from '@mantine/core';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MemoryRouter } from 'react-router-dom';

// Mock Redux store for testing
const createTestStore = () => {
  return configureStore({
    reducer: {
      ui: (state = { activePagePath: '/' }, action) => {
        if (action.type === 'ui/setActivePage') {
          return { ...state, activePagePath: action.payload };
        }
        return state;
      },
      config: (state = { config: {} }, action) => {
        if (action.type === 'config/updateConfig') {
          return { ...state, config: { ...state.config, ...action.payload } };
        }
        return state;
      }
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false,
        immutableCheck: false,
      }),
  });
};

// Props for the MantineTestProvider component
interface MantineTestProviderProps {
  children: ReactNode;
  colorScheme?: 'light' | 'dark';
  withRouter?: boolean;
  withRedux?: boolean;
  initialRoute?: string;
  preloadedState?: Record<string, any>;
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
  initialRoute = '/',
  preloadedState,
}) => {
  // Create store for tests that need Redux
  const store = createTestStore();

  // Create the theme for Mantine
  const theme = {
    colorScheme,
    primaryColor: 'blue',
    defaultRadius: 'sm',
    colors: {
      blue: ['#E7F5FF', '#D0EBFF', '#A5D8FF', '#74C0FC', '#4DABF7', '#339AF0', '#228BE6', '#1C7ED6', '#1971C2', '#1864AB'],
      gray: ['#F8F9FA', '#F1F3F5', '#E9ECEF', '#DEE2E6', '#CED4DA', '#ADB5BD', '#868E96', '#495057', '#343A40', '#212529'],
      dark: ['#C1C2C5', '#A6A7AB', '#909296', '#5C5F66', '#373A40', '#2C2E33', '#25262B', '#1A1B1E', '#141517', '#101113'],
    },
    spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 },
    breakpoints: { xs: '30em', sm: '48em', md: '64em', lg: '74em', xl: '90em' },
  };

  // Start with the base wrapper
  let wrappedContent = (
    <MantineProvider 
      theme={theme}
      withGlobalStyles 
      withNormalizeCSS
    >
      {children}
    </MantineProvider>
  );

  // Add Router wrapper if requested
  if (withRouter) {
    wrappedContent = (
      <MemoryRouter initialEntries={[initialRoute]}>
        {wrappedContent}
      </MemoryRouter>
    );
  }

  // Add Redux wrapper if requested
  if (withRedux) {
    wrappedContent = (
      <Provider store={store}>
        {wrappedContent}
      </Provider>
    );
  }

  return wrappedContent;
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