/**
 * Custom testing environment setup for Vitest
 * This file ensures proper environment setup for all tests
 */

import { beforeAll, vi } from 'vitest';

/**
 * Sets up all required browser mocks and environment variables for tests
 */
function setupTestingEnvironment() {
  // Setup window.matchMedia - this is crucial for Mantine components
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches: query.includes('prefers-color-scheme: dark') ? false : true,
    media: query,
    onchange: null,
    addListener: vi.fn(), // Deprecated
    removeListener: vi.fn(), // Deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));

  // Setup getComputedStyle for Mantine
  window.getComputedStyle = vi.fn().mockImplementation(() => ({
    getPropertyValue: (prop) => {
      if (prop === '--mantine-color-scheme') return 'light';
      return 'rgb(0, 0, 0)';
    },
    display: 'block',
    visibility: 'visible',
    opacity: '1',
  }));

  // Setup ResizeObserver
  class ResizeObserverMock {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }
  window.ResizeObserver = ResizeObserverMock as any;

  // Setup IntersectionObserver
  class IntersectionObserverMock {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
    takeRecords = vi.fn();
    root = null;
    rootMargin = '';
    thresholds = [];
  }
  window.IntersectionObserver = IntersectionObserverMock as any;

  // Setup Element scrolling methods
  Element.prototype.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  window.scrollTo = vi.fn();

  // Setup localStorage
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    },
    writable: true,
  });
}

// Call the setup function immediately when this module is imported
setupTestingEnvironment();

// Export function to allow explicit setup in test files if needed
export { setupTestingEnvironment };