/**
 * Setup for Jest DOM matchers for Vitest
 * This file is imported by testing-setup.tsx
 */

// Set up matchMedia for JSDOM first
if (typeof window !== 'undefined') {
  window.matchMedia = window.matchMedia || function matchMedia(query) {
    return {
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => {},
    };
  };
}

// Import actual Jest DOM matchers
import * as jestDom from '@testing-library/jest-dom/matchers';
import { expect, vi } from 'vitest';

// Define an interface for JestDOM matchers
interface CustomMatchers<R = unknown> {
  toBeInTheDocument(): R;
  toHaveAttribute(attr: string, value?: string): R;
  toHaveTextContent(text: string, options?: { normalizeWhitespace: boolean }): R;
  toBeChecked(): R;
  toBeDisabled(): R;
  toBeEnabled(): R;
  toBeEmpty(): R;
  toBeInvalid(): R;
  toBeRequired(): R;
  toBeValid(): R;
  toBeVisible(): R;
  toContainElement(element: HTMLElement | null): R;
  toContainHTML(html: string): R;
  toHaveClass(...classNames: string[]): R;
  toHaveFocus(): R;
  toHaveFormValues(expectedValues: Record<string, any>): R;
  toHaveStyle(css: string): R;
  toHaveValue(value?: string | string[] | number): R;
}

// Extend Vitest's expect
declare global {
  namespace Vi {
    interface Assertion extends CustomMatchers {}
    interface AsymmetricMatchersContaining extends CustomMatchers {}
  }
}

// Extend Vitest's expect with custom matchers
// This ensures jest-dom matchers are properly mapped to Vitest
expect.extend({
  toBeInTheDocument(received) {
    const element = received instanceof Element
      ? received
      : received?.ownerDocument?.documentElement;
    
    const pass = element !== null && element !== undefined && 
      document.body.contains(element);
    
    return {
      pass,
      message: () => pass 
        ? `Expected element not to be in the document`
        : `Expected element to be in the document`,
    };
  },
  
  toHaveAttribute(received, attr, value) {
    const hasAttr = received && typeof received.hasAttribute === 'function' && received.hasAttribute(attr);
    const attrValue = hasAttr ? received.getAttribute(attr) : undefined;
    const pass = hasAttr && (value === undefined || attrValue === value);
    
    return {
      pass,
      message: () => pass
        ? `Expected element not to have attribute "${attr}"${value ? ` with value "${value}"` : ''}`
        : `Expected element to have attribute "${attr}"${value ? ` with value "${value}"` : ''}${hasAttr ? ` but had value "${attrValue}"` : ''}`,
    };
  },
  
  toHaveTextContent(received, text, options = { normalizeWhitespace: false }) {
    if (!received || typeof received.textContent !== 'string') {
      return {
        pass: false,
        message: () => `Expected to receive an HTMLElement but got ${typeof received}`,
      };
    }
    
    let content = received.textContent;
    if (options.normalizeWhitespace) {
      content = content.replace(/\s+/g, ' ').trim();
    }
    
    const pass = content.includes(text);
    
    return {
      pass,
      message: () => pass
        ? `Expected element not to have text content "${text}" but it did`
        : `Expected element to have text content "${text}" but found "${content}"`,
    };
  },
  
  // Implementation for common matchers
  toBeDisabled(received) {
    const isDisabled = received.disabled === true ||
                      received.getAttribute('aria-disabled') === 'true' ||
                      received.hasAttribute('disabled');

    return {
      pass: isDisabled,
      message: () => isDisabled
        ? `Expected element not to be disabled, but it was`
        : `Expected element to be disabled, but it wasn't`,
    };
  },

  toBeVisible(received) {
    // Check if element exists in DOM and is visible
    const isVisible = received &&
                     window.getComputedStyle(received).display !== 'none' &&
                     window.getComputedStyle(received).visibility !== 'hidden' &&
                     window.getComputedStyle(received).opacity !== '0';

    return {
      pass: isVisible,
      message: () => isVisible
        ? `Expected element not to be visible, but it was`
        : `Expected element to be visible, but it wasn't`,
    };
  },

  toHaveClass(received, ...classNames) {
    const classList = received?.classList ? Array.from(received.classList) : [];
    const hasAllClasses = classNames.every(className => classList.includes(className));

    return {
      pass: hasAllClasses,
      message: () => hasAllClasses
        ? `Expected element not to have classes "${classNames.join(', ')}", but it did`
        : `Expected element to have classes "${classNames.join(', ')}", but it had "${classList.join(', ')}"`,
    };
  },

  // Add all other matchers from @testing-library/jest-dom
  // This ensures they're available in Vitest
  ...jestDom,
});

// Global declarations to help with testing
declare global {
  interface Window {
    HTMLElement: typeof HTMLElement;
  }
}

// Set up the testing environment
beforeEach(() => {
  // Clean up document between tests to prevent multiple elements with same IDs
  if (document.body) {
    document.body.innerHTML = '';
  }
});

afterEach(() => {
  // Clean up document after each test
  if (document.body) {
    document.body.innerHTML = '';
  }
});