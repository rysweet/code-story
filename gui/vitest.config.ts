import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { configDefaults } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
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
    // Isolate each test file
    isolate: true,
  },
});