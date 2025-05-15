import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface UiState {
  activePage: string;
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  notifications: Array<{
    id: string;
    type: 'info' | 'success' | 'warning' | 'error';
    message: string;
    timeout?: number;
  }>;
}

const initialState: UiState = {
  activePage: 'graph',
  sidebarCollapsed: false,
  theme: 'light',
  notifications: [],
};

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setActivePage: (state, action: PayloadAction<string>) => {
      state.activePage = action.payload;
    },
    toggleSidebar: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
    },
    setTheme: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme = action.payload;
    },
    addNotification: (
      state,
      action: PayloadAction<{
        type: 'info' | 'success' | 'warning' | 'error';
        message: string;
        timeout?: number;
      }>
    ) => {
      const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      state.notifications.push({
        id,
        ...action.payload,
      });
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(
        (n) => n.id !== action.payload
      );
    },
    clearNotifications: (state) => {
      state.notifications = [];
    },
  },
});

export const {
  setActivePage,
  toggleSidebar,
  setTheme,
  addNotification,
  removeNotification,
  clearNotifications,
} = uiSlice.actions;

export default uiSlice.reducer;