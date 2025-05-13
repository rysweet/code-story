/**
 * Global setup file for Vitest
 * This sets up the environment before any tests run
 */

// Import Vitest
import { vi } from 'vitest';

// Define matchMedia mock globally
global.matchMedia = function matchMedia(query) {
  return {
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // Deprecated
    removeListener: vi.fn(), // Deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  };
};

// Define document if needed (for Node environment)
if (typeof document === 'undefined') {
  global.document = {
    createElement: vi.fn(),
    body: {
      appendChild: vi.fn(),
      contains: vi.fn(),
    },
  };
}

// Define window for Node environment
if (typeof window === 'undefined') {
  global.window = {
    matchMedia: global.matchMedia,
    getComputedStyle: vi.fn(() => ({
      getPropertyValue: vi.fn(() => ''),
    })),
  };
}