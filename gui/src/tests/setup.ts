/**
 * Main setup file for Vitest tests
 * This is the primary setup file that's loaded for all tests
 */

// Import our environment setup which mocks browser APIs
import './testing-environment';

// Import our Jest-DOM setup (after environment setup)
import './jest-dom';

// Import React Testing Library cleanup
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, beforeAll, afterAll, vi } from 'vitest';

// Make vitest test globals available to test files
global.beforeEach = beforeEach;
global.afterEach = afterEach;
global.beforeAll = beforeAll;
global.afterAll = afterAll;
global.vi = vi;

// Add global testing aliases for compatibility with older tests
global.test = global.it = global.test || vi.fn();
global.describe = global.describe || vi.fn();
global.expect = global.expect || vi.fn();

// Ensure document is defined
if (typeof document === 'undefined') {
  global.document = window.document;
}

// Clean up after each test - this is in addition to the cleanup in testing-environment.ts
// to ensure both approaches work
afterEach(() => {
  // Run Testing Library cleanup to unmount React trees
  cleanup();

  // Reset any mocks between tests
  vi.clearAllMocks();
  vi.resetAllMocks();

  // Clear any timers that might remain between tests
  vi.clearAllTimers();
});