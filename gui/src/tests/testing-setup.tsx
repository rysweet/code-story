/**
 * Setup file for React Testing Library and testing utilities
 * This provides a custom render function that includes all necessary providers
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';

// Import our environment setup
import './testing-environment';

// Import our Jest-DOM setup
import './jest-dom';

// Import our Mantine test provider with all providers
import { withAllProviders } from './MantineTestProvider';

/**
 * Custom render that wraps components with all required providers
 * This combines Redux, Router, and Mantine UI providers
 */
function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(withAllProviders(ui), options);
}

// Re-export everything from React Testing Library
export * from '@testing-library/react';

// Override render method with our custom render
export { customRender as render };

// Export Mantine providers for cases where direct access is needed
export { MantineTestProvider, withMantine, withAllProviders } from './MantineTestProvider';