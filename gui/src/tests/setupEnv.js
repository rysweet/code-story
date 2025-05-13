/**
 * Environment setup for tests
 * This file sets up global variables needed by the DOM testing environment.
 * It must be a .js file to ensure it loads before TypeScript parsing.
 */

if (!global.window) {
  global.window = {};
}

// Mock window.matchMedia
if (!global.window.matchMedia) {
  global.window.matchMedia = function matchMedia(query) {
    return {
      matches: false,
      media: query,
      onchange: null,
      addListener: function() {},
      removeListener: function() {},
      addEventListener: function() {},
      removeEventListener: function() {},
      dispatchEvent: function() {},
    };
  };
}

// Create matchMedia mock on global as well
if (!global.matchMedia) {
  global.matchMedia = global.window.matchMedia;
}

// Ensure document exists
if (!global.document) {
  global.document = {
    createElement: function() { return {}; },
    body: {
      appendChild: function() {},
      contains: function() { return true; },
    },
  };
}

// Create Element if it doesn't exist
if (!global.Element) {
  global.Element = class Element {
    constructor() {}
    scrollTo() {}
    scrollIntoView() {}
  };
}

console.log('Environment setup complete - matchMedia mocked globally');