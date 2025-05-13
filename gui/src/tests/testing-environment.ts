/**
 * Custom testing environment setup for Vitest
 * This file ensures proper environment setup for all tests
 */

import { beforeAll, beforeEach, afterEach, vi } from 'vitest';

/**
 * Sets up all required browser mocks and environment variables for tests
 */
function setupTestingEnvironment() {
  // Ensure setupTestingEnvironment is called before any tests run
  beforeAll(() => {
    console.log("Setting up testing environment globals...");

    // Fix for window.matchMedia which is not available in JSDOM
    Object.defineProperty(global, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: query.includes('prefers-color-scheme: dark') ? false : true,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    // Define window.matchMedia if it doesn't exist
    if (window && !window.matchMedia) {
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation(query => ({
          matches: query.includes('prefers-color-scheme: dark') ? false : true,
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });
    }

    // Setup getComputedStyle for Mantine
    if (window) {
      window.getComputedStyle = vi.fn().mockImplementation(() => ({
        getPropertyValue: (prop) => {
          if (prop === '--mantine-color-scheme') return 'light';
          return 'rgb(0, 0, 0)';
        },
        display: 'block',
        visibility: 'visible',
        opacity: '1',
      }));
    }

    // Setup ResizeObserver
    class ResizeObserverMock {
      observe = vi.fn();
      unobserve = vi.fn();
      disconnect = vi.fn();
    }
    if (window) {
      window.ResizeObserver = ResizeObserverMock as any;
    }

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
    if (window) {
      window.IntersectionObserver = IntersectionObserverMock as any;
    }

    // Setup Element scrolling methods
    if (typeof Element !== 'undefined') {
      Element.prototype.scrollTo = vi.fn();
      Element.prototype.scrollIntoView = vi.fn();
    }

    if (window) {
      window.scrollTo = vi.fn();
    }

    // Setup localStorage
    if (window) {
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

    // Ensure we have a document body
    if (typeof document !== 'undefined' && !document.body) {
      const body = document.createElement('body');
      document.appendChild(body);
    }
  });

  // Clean up after each test
  beforeEach(() => {
    if (typeof document !== 'undefined' && document.body) {
      document.body.innerHTML = '';
    }
  });

  afterEach(() => {
    if (typeof document !== 'undefined' && document.body) {
      document.body.innerHTML = '';
    }
    vi.clearAllMocks();
  });
}

// Call the setup function immediately when this module is imported
setupTestingEnvironment();

// Export function to allow explicit setup in test files if needed
export { setupTestingEnvironment };