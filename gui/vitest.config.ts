import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { configDefaults } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    // We need to use globalSetup for some configurations that must happen before JSDOM
    globalSetup: './src/tests/global-setup.js',
    setupFiles: [
      './src/tests/testing-environment.ts',
      './src/tests/setup.ts',
      './src/tests/testing-setup.tsx'
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