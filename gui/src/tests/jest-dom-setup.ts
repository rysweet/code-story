/**
 * Setup for Jest DOM matchers for Vitest
 * This file is imported by testing-setup.tsx
 */

// Import Testing Library matchers
import '@testing-library/jest-dom';
import { expect } from 'vitest';

// Add missing matchers from jest-dom
import * as matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect
expect.extend(matchers);

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

// Global declarations to help with testing
declare global {
  interface Window {
    HTMLElement: typeof HTMLElement;
  }
}

// Make sure document body exists (JSDOM may not initialize it)
if (typeof document !== 'undefined' && !document.body) {
  const body = document.createElement('body');
  document.body = body;
}