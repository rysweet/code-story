import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { configDefaults } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/tests/setup.ts',
    css: false,
    include: ['**/*.{test,spec}.{js,jsx,ts,tsx}'],
    exclude: [...configDefaults.exclude, 'e2e/**'],
    deps: {
      inline: ['msw'],
    },
    environmentOptions: {
      jsdom: {
        resources: 'usable',
      },
    },
  },
});