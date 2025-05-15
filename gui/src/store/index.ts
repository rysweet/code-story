import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';

import uiReducer from './slices/uiSlice';
import configReducer from './slices/configSlice';
import { baseApi } from './api/baseApi';

export const store = configureStore({
  reducer: {
    ui: uiReducer,
    config: configReducer,
    [baseApi.reducerPath]: baseApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(baseApi.middleware),
});

// Enable refetchOnFocus and refetchOnReconnect behaviors
setupListeners(store.dispatch);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Export all API hooks for convenience
export * from './api/graphApi';
export * from './api/ingestApi';
export * from './api/configApi';
export * from './api/serviceApi';
export * from './api/mcpApi';