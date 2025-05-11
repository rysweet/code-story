const Environment = require('jest-environment-jsdom').default;
const { TextEncoder, TextDecoder } = require('util');

/**
 * A custom environment to run tests with JSDOM
 */
module.exports = class CustomTestEnvironment extends Environment {
  async setup() {
    await super.setup();
    
    // Set globals that are expected in browser environments
    if (typeof this.global.TextEncoder === 'undefined') {
      this.global.TextEncoder = TextEncoder;
      this.global.TextDecoder = TextDecoder;
    }
    
    // Mock window.matchMedia
    this.global.matchMedia = (query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => {},
    });
    
    // Mock window.scrollTo
    this.global.scrollTo = () => {};
    
    // Mock ResizeObserver
    this.global.ResizeObserver = class ResizeObserver {
      constructor(callback) {
        this.callback = callback;
      }
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  }
};