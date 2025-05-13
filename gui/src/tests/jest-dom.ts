/**
 * This file provides Jest-DOM matchers support for Vitest.
 * It's used to ensure proper compatibility between Testing Library, Jest-DOM, and Vitest.
 */

import matchers from '@testing-library/jest-dom/matchers';
import { expect } from 'vitest';

// Directly extend the Vitest expect with all Jest-DOM matchers
expect.extend(matchers);

// Add any missing matchers that might not be properly imported
expect.extend({
  toBeInTheDocument(received) {
    const isElement = received && received.nodeType === Node.ELEMENT_NODE;
    const isInDocument = document.body.contains(received);
    const pass = isElement && isInDocument;
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
    const attrValue = received && received.hasAttribute && received.hasAttribute(attr) 
      ? received.getAttribute(attr) 
      : undefined;
    const pass = hasAttr && (value === undefined || attrValue === value);
    
    return {
      pass,
      message: () =>
        pass
          ? `Expected element not to have attribute "${attr}"${value ? ` with value "${value}"` : ''}`
          : `Expected element to have attribute "${attr}"${value ? ` with value "${value}"` : ''}${
              hasAttr ? ` but had value "${attrValue}"` : ''
            }`,
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
    
    const hasText = content.includes(text);
    
    return {
      pass: hasText,
      message: () =>
        hasText
          ? `Expected element not to have text content "${text}" but it did`
          : `Expected element to have text content "${text}" but found "${content}"`,
    };
  },
});

// Make DOM testing library matchers available globally
declare global {
  namespace Vi {
    interface JestAssertion<T = any> extends jest.Matchers<void, T> {
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