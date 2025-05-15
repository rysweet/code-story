const Environment = require('jest-environment-jsdom');

/**
 * Custom test environment for JSDOM
 */
module.exports = class TestEnvironment extends Environment {
  constructor(config, context) {
    super(config, context);
    
    // Add properties to the environment.context object,
    // which will be passed to test files
    this.global.process.env = {
      ...this.global.process.env,
      VITE_API_URL: 'http://localhost:8000',
    };
  }

  async setup() {
    await super.setup();
    this.global.setImmediate = setTimeout;
    
    // Mock window properties not implemented in jsdom
    Object.defineProperty(this.global.window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
  }
};