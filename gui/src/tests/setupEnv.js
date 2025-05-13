/**
 * Environment setup for tests
 * This file sets up global variables needed by the DOM testing environment.
 * It must be a .js file to ensure it loads before TypeScript parsing.
 */

// First ensure we have a window object
if (typeof window === 'undefined') {
  global.window = {};
}

// Mock window.matchMedia - this must be defined before any tests run
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  configurable: true,
  value: (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Jest compatibility
    removeListener: jest.fn(), // Jest compatibility
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }),
});

// Also define on global for direct imports that might use it
global.matchMedia = window.matchMedia;

// ResizeObserver mock - many Mantine components need this
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Define ResizeObserver if it doesn't exist
if (typeof window.ResizeObserver === 'undefined') {
  window.ResizeObserver = ResizeObserverMock;
  global.ResizeObserver = ResizeObserverMock;
}

// Ensure document body exists for tests
if (typeof document !== 'undefined' && !document.body) {
  const body = document.createElement('body');
  document.body = body;
}

// Define localStorage mock
if (typeof window.localStorage === 'undefined') {
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: jest.fn(() => null),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
    },
    writable: true,
  });
}

// Create getComputedStyle mock for Mantine
if (typeof window.getComputedStyle === 'undefined') {
  window.getComputedStyle = () => ({
    getPropertyValue: () => '',
    display: 'block',
    visibility: 'visible',
    opacity: '1',
  });
}

// Create Element prototype methods if needed
if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = jest.fn();
  Element.prototype.scrollTo = jest.fn();
}

// Define global test functions (for Jest compatibility)
global.jest = {
  fn: () => jest.fn(),
};

// Make Jest-like functions available globally
global.beforeEach = global.beforeEach || function() {};
global.afterEach = global.afterEach || function() {};
global.beforeAll = global.beforeAll || function() {};
global.afterAll = global.afterAll || function() {};

// Setup automatic cleanup between tests
if (typeof global.afterEach === 'function') {
  global.afterEach(() => {
    if (document.body) {
      document.body.innerHTML = '';
    }
  });
}

console.log('Environment setup complete - test environment is ready');