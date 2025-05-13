/**
 * Setup file for React Testing Library and testing utilities
 */

import React, { ReactElement, ReactNode } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { rootReducer } from '../store';

// Import our custom Jest DOM matchers setup
import './jest-dom-setup';

// Import matchMedia mock
import './mocks/matchMedia';

// Import our Mantine test provider
import { MantineTestProvider } from './MantineTestProvider';

// Create a custom renderer that includes all providers (Redux, Router, Mantine)
const AllProviders = ({ children }: { children: ReactNode }) => {
  const store = configureStore({
    reducer: rootReducer,
    // Add any middleware or enhancers needed for tests
  });

  return (
    <Provider store={store}>
      <BrowserRouter>
        <MantineTestProvider>
          {children}
        </MantineTestProvider>
      </BrowserRouter>
    </Provider>
  );
};

// Custom render function that wraps with all providers
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllProviders, ...options });

// Re-export everything from react-testing-library
export * from '@testing-library/react';

// Override render method
export { customRender as render };

// Clean up document between tests
beforeEach(() => {
  document.body.innerHTML = '';
});

afterEach(() => {
  document.body.innerHTML = '';
});