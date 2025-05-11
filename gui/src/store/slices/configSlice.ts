import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ConfigState {
  isLoading: boolean;
  error: string | null;
  schema: Record<string, any> | null;
  config: Record<string, any>;
  isDirty: boolean;
}

const initialState: ConfigState = {
  isLoading: false,
  error: null,
  schema: null,
  config: {},
  isDirty: false,
};

export const configSlice = createSlice({
  name: 'config',
  initialState,
  reducers: {
    fetchConfigStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    fetchConfigSuccess: (state, action: PayloadAction<Record<string, any>>) => {
      state.isLoading = false;
      state.config = action.payload;
      state.isDirty = false;
    },
    fetchConfigFailure: (state, action: PayloadAction<string>) => {
      state.isLoading = false;
      state.error = action.payload;
    },
    fetchSchemaStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    fetchSchemaSuccess: (state, action: PayloadAction<Record<string, any>>) => {
      state.isLoading = false;
      state.schema = action.payload;
    },
    fetchSchemaFailure: (state, action: PayloadAction<string>) => {
      state.isLoading = false;
      state.error = action.payload;
    },
    updateConfigField: (
      state,
      action: PayloadAction<{ path: string; value: any }>
    ) => {
      const { path, value } = action.payload;
      
      // For nested paths like 'section.field'
      const parts = path.split('.');
      let current = state.config;
      
      // Create path if it doesn't exist
      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        if (!current[part]) {
          current[part] = {};
        }
        current = current[part];
      }
      
      current[parts[parts.length - 1]] = value;
      state.isDirty = true;
    },
    saveConfigStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    saveConfigSuccess: (state) => {
      state.isLoading = false;
      state.isDirty = false;
    },
    saveConfigFailure: (state, action: PayloadAction<string>) => {
      state.isLoading = false;
      state.error = action.payload;
    },
    resetConfig: (state) => {
      state.isDirty = false;
    },
  },
});

export const {
  fetchConfigStart,
  fetchConfigSuccess,
  fetchConfigFailure,
  fetchSchemaStart,
  fetchSchemaSuccess,
  fetchSchemaFailure,
  updateConfigField,
  saveConfigStart,
  saveConfigSuccess,
  saveConfigFailure,
  resetConfig,
} = configSlice.actions;

export default configSlice.reducer;