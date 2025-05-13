// Import the custom jest-dom matchers setup
import './jest-dom';
import '@testing-library/jest-dom';
import { afterEach, beforeEach, beforeAll, afterAll, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// Make vitest test globals available to test files
// This fixes the "beforeEach is not defined" errors
global.beforeEach = beforeEach;
global.afterEach = afterEach;
global.beforeAll = beforeAll;
global.afterAll = afterAll;
global.vi = vi;

// Add global testing aliases
global.test = global.it = global.test || vi.fn();
global.describe = global.describe || vi.fn();
global.expect = global.expect || vi.fn();

// Ensure document is defined
if (typeof document === 'undefined') {
  global.document = window.document;
}

// Initialize required browser mocks before tests
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

global.matchMedia = vi.fn().mockImplementation((query) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
}));

// Set up all required browser APIs
beforeAll(() => {
  // Mock window.matchMedia properly
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });

  // Mock getComputedStyle
  Object.defineProperty(window, 'getComputedStyle', {
    value: () => ({
      getPropertyValue: (prop) => {
        return prop === '--mantine-color-scheme' ? 'light' : 'rgb(0, 0, 0)';
      },
    }),
  });

  // Mock scrolling methods
  window.scrollTo = vi.fn();
  Element.prototype.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  window.HTMLElement.prototype.scrollIntoView = vi.fn();

  // Mock localStorage
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    },
    writable: true,
  });

  // Mock IntersectionObserver
  class IntersectionObserverMock {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
    root = null;
    rootMargin = '';
    thresholds = [];
    takeRecords = vi.fn();
  }
  window.IntersectionObserver = IntersectionObserverMock;

  // Fix property that Mantine checks for dark mode
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => {
      return {
        matches: query.includes('prefers-color-scheme: dark') ? false : false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      };
    }),
  });
});

// Ensure tests run in isolation
beforeEach(() => {
  // Reset document body before each test to ensure clean state
  document.body.innerHTML = '';
});

// Clean up after each test
afterEach(() => {
  // This ensures we don't get "Found multiple elements" errors in tests
  // by cleaning up the DOM after each test
  document.body.innerHTML = '';
  // Run Testing Library cleanup to unmount React trees
  cleanup();
  // Reset any mocks between tests
  vi.clearAllMocks();
  // Clear any queries that might remain between tests
  vi.clearAllTimers();
});