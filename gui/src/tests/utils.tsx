import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore, combineReducers } from '@reduxjs/toolkit';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { MantineProvider } from '@mantine/core';

import uiReducer from '../store/slices/uiSlice';
import configReducer from '../store/slices/configSlice';
import { baseApi } from '../store/api/baseApi';
import { injectStoreMiddleware } from './middleware';

// Suppress React Router warning about future flags
// This approach simply suppresses the console warnings rather than enabling the flags
const originalConsoleWarn = console.warn;
console.warn = function(...args) {
  // Filter out React Router future flag warnings
  if (args[0] && typeof args[0] === 'string' && 
      (args[0].includes('React Router Future Flag Warning') || 
       args[0].includes('v7_startTransition') || 
       args[0].includes('v7_relativeSplatPath'))) {
    return;
  }
  originalConsoleWarn.apply(console, args);
};

// Helper to create a mock store
export function createMockStore(preloadedState = {}) {
  const rootReducer = combineReducers({
    ui: uiReducer,
    config: configReducer,
    [baseApi.reducerPath]: baseApi.reducer,
  });

  return configureStore({
    reducer: rootReducer,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        // This prevents serializability errors in tests
        serializableCheck: false,
      }).concat(baseApi.middleware),
    preloadedState: preloadedState as any,
  });
}

// Custom render for components with providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  preloadedState?: Record<string, any>;
  store?: ReturnType<typeof createMockStore>;
  route?: string;
  path?: string;
  withMantine?: boolean;
}

// Custom render function
export function renderWithProviders(
  ui: ReactElement,
  {
    preloadedState = {},
    store = createMockStore(preloadedState),
    route = '/',
    path = '/',
    withMantine = true,
    ...renderOptions
  }: CustomRenderOptions = {}
) {
  // Wrapper component that provides context providers
  function AllProviders({ children }: { children: React.ReactNode }) {
    const content = (
      <MemoryRouter initialEntries={[route]}>
        {path === route ? (
          children
        ) : (
          <Routes>
            <Route path={path} element={children} />
          </Routes>
        )}
      </MemoryRouter>
    );

    // When testing mocked Mantine components, we don't need the MantineProvider
    // as we're mocking all the Mantine components directly
    return (
      <Provider store={store}>
        {withMantine ? <MantineProvider>{content}</MantineProvider> : content}
      </Provider>
    );
  }

  return {
    store,
    ...render(ui, { wrapper: AllProviders, ...renderOptions }),
  };
}