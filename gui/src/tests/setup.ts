/**
 * Main setup file for Vitest tests
 * This is the primary setup file that's loaded for all tests
 */

// Import our Jest-DOM setup - provides all custom testing matchers
import './jest-dom-setup';

// Import React Testing Library cleanup
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, beforeAll, afterAll, vi } from 'vitest';

// Make sure the window and document exist
if (typeof window === 'undefined') {
  global.window = {} as any;
}

if (typeof document === 'undefined') {
  global.document = {} as any;
}

// Create matchMedia mock if it doesn't exist
if (!global.matchMedia) {
  global.matchMedia = vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

// Make sure window.matchMedia is defined
if (!window.matchMedia) {
  window.matchMedia = global.matchMedia;
}

// Define global Jest-compatible functions
global.jest = {
  fn: vi.fn,
  mock: vi.mock,
  spyOn: vi.spyOn,
};

// Create global Jest-compatible aliases
global.beforeEach = beforeEach;
global.afterEach = afterEach;
global.beforeAll = beforeAll;
global.afterAll = afterAll;
global.test = global.it = vi.it;
global.describe = vi.describe;
global.expect = vi.expect;

// Clean up after each test
afterEach(() => {
  // Run Testing Library cleanup to unmount React trees
  cleanup();

  // Reset any mocks between tests
  vi.clearAllMocks();
  vi.resetAllMocks();

  // Clear any timers that might remain between tests
  vi.clearAllTimers();
});