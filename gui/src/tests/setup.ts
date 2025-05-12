import '@testing-library/jest-dom';
import { expect, afterEach, beforeAll, afterAll, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import matchers from '@testing-library/jest-dom/matchers';

// Ensure document is defined
if (typeof document === 'undefined') {
  global.document = window.document;
}

// Extend vitest's expect method with methods from react-testing-library
// This adds custom matchers like toBeInTheDocument(), toHaveAttribute(), etc.
expect.extend(matchers);

// Add missing matchers from jest-dom that might not be properly imported
expect.extend({
  toBeInTheDocument(received) {
    const pass = received !== null && received !== undefined;
    return {
      pass,
      message: () =>
        pass
          ? `Expected element not to be in the document`
          : `Expected element to be in the document`,
    };
  },
  toHaveAttribute(received, attr, value) {
    const hasAttr = received && received.hasAttribute && received.hasAttribute(attr);
    const pass = hasAttr && (value === undefined || received.getAttribute(attr) === value);
    return {
      pass,
      message: () =>
        pass
          ? `Expected element not to have attribute "${attr}"${value ? ` with value "${value}"` : ''}`
          : `Expected element to have attribute "${attr}"${value ? ` with value "${value}"` : ''}`,
    };
  },
  toHaveTextContent(received, text) {
    const hasText = received && typeof received.textContent === 'string' &&
      received.textContent.includes(text);
    return {
      pass: hasText,
      message: () =>
        hasText
          ? `Expected element not to have text content "${text}"`
          : `Expected element to have text content "${text}"`,
    };
  }
});

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

// Clean up after each test
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});