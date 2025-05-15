import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { configDefaults } from 'vitest/config';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [
      './src/tests/setupEnv.js',
      './src/tests/setup.ts'
    ],
    css: false,
    include: ['**/*.{test,spec}.{js,jsx,ts,tsx}'],
    exclude: [...configDefaults.exclude, 'e2e/**'],
    deps: {
      inline: ['msw', '@testing-library/jest-dom'],
    },
    environmentOptions: {
      jsdom: {
        resources: 'usable',
      },
    },
    // Enable more Jest-compatible behavior
    passWithNoTests: true,
    restoreMocks: true,
    clearMocks: true,
    mockReset: true,
    // Expose globals explicitly
    define: {
      'globalThis.beforeEach': 'beforeEach',
      'globalThis.afterEach': 'afterEach',
      'window.matchMedia': 'matchMedia',
    },
    // Isolate each test file
    isolate: false, // Set to false to allow proper setup of global mocks
  },
});