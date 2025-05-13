/**
 * This file provides Jest-DOM matchers support for Vitest.
 * It's used to ensure proper compatibility between Testing Library, Jest-DOM, and Vitest.
 */

import * as matchers from '@testing-library/jest-dom/matchers';
import { expect, beforeAll } from 'vitest';

// Set up on beforeAll to ensure it's applied at the right time
beforeAll(() => {
  console.log("Setting up Jest-DOM matchers for Vitest...");

  try {
    // Fix for window.matchMedia which is required by @testing-library/jest-dom
    if (typeof window !== 'undefined' && !window.matchMedia) {
      window.matchMedia = (query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => {},
      });
    }

    // Directly extend the Vitest expect with all Jest-DOM matchers
    expect.extend(matchers);

    // Add implementation for toBeInTheDocument matcher
    expect.extend({
      toBeInTheDocument(received) {
        if (!received || typeof received !== 'object') {
          return {
            pass: false,
            message: () => `Expected to receive an HTML element but got ${typeof received}`,
          };
        }

        const isElement = received &&
                         received.nodeType === (typeof Node !== 'undefined' ? Node.ELEMENT_NODE : 1);
        const isInDocument = document.body && document.body.contains(received);
        const pass = isElement && isInDocument;

        return {
          pass,
          message: () => pass
            ? `Expected element not to be in the document`
            : `Expected element to be in the document`,
        };
      },

      toHaveAttribute(received, attr, value) {
        if (!received || typeof received !== 'object') {
          return {
            pass: false,
            message: () => `Expected to receive an HTML element but got ${typeof received}`,
          };
        }

        const hasAttr = received.hasAttribute && received.hasAttribute(attr);
        const attrValue = hasAttr ? received.getAttribute(attr) : undefined;
        const pass = hasAttr && (value === undefined || attrValue === value);

        return {
          pass,
          message: () => pass
            ? `Expected element not to have attribute "${attr}"${value ? ` with value "${value}"` : ''}`
            : `Expected element to have attribute "${attr}"${value ? ` with value "${value}"` : ''}${
              hasAttr ? ` but had value "${attrValue}"` : ''
            }`,
        };
      },

      toHaveTextContent(received, text, options = { normalizeWhitespace: false }) {
        if (!received || typeof received !== 'object' || typeof received.textContent !== 'string') {
          return {
            pass: false,
            message: () => `Expected to receive an HTML element but got ${typeof received}`,
          };
        }

        let content = received.textContent;
        if (options.normalizeWhitespace) {
          content = content.replace(/\s+/g, ' ').trim();
        }

        const hasText = content.includes(text);

        return {
          pass: hasText,
          message: () => hasText
            ? `Expected element not to have text content "${text}" but it did`
            : `Expected element to have text content "${text}" but found "${content}"`,
        };
      },

      toBeVisible(received) {
        if (!received || typeof received !== 'object') {
          return {
            pass: false,
            message: () => `Expected to receive an HTML element but got ${typeof received}`,
          };
        }

        // Check element is displayed
        const isVisible = received &&
                         !!received.offsetWidth &&
                         !!received.offsetHeight &&
                         received.style.display !== 'none';

        return {
          pass: isVisible,
          message: () => isVisible
            ? `Expected element not to be visible, but it was`
            : `Expected element to be visible, but it wasn't`,
        };
      },

      toBeDisabled(received) {
        if (!received || typeof received !== 'object') {
          return {
            pass: false,
            message: () => `Expected to receive an HTML element but got ${typeof received}`,
          };
        }

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
    });

    console.log("Jest-DOM matchers set up successfully.");
  } catch (error) {
    console.error("Error setting up Jest-DOM matchers:", error);
  }
});

// Define interface for the Jest-DOM matchers to be available in TypeScript
declare global {
  namespace Vi {
    interface JestAssertion<T = any> {
      // Add the missing Jest-DOM matchers here
      toBeInTheDocument(): T;
      toHaveAttribute(attr: string, value?: string): T;
      toHaveTextContent(text: string, options?: { normalizeWhitespace: boolean }): T;
      toBeChecked(): T;
      toBeDisabled(): T;
      toBeEnabled(): T;
      toBeEmpty(): T;
      toBeInvalid(): T;
      toBeRequired(): T;
      toBeValid(): T;
      toBeVisible(): T;
      toContainElement(element: HTMLElement | null): T;
      toContainHTML(html: string): T;
      toHaveClass(...classNames: string[]): T;
      toHaveFocus(): T;
      toHaveFormValues(expectedValues: Record<string, any>): T;
      toHaveStyle(css: string): T;
      toHaveValue(value?: string | string[] | number): T;
    }
  }
}