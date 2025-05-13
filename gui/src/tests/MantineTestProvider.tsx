/**
 * Test provider component for Mantine UI
 * This provides the necessary context for Mantine components in tests
 */
import React, { ReactNode } from 'react';
import { MantineProvider, ColorSchemeProvider } from '@mantine/core';

// Props for the MantineTestProvider component
interface MantineTestProviderProps {
  children: ReactNode;
  colorScheme?: 'light' | 'dark';
}

/**
 * Test provider that wraps Mantine components with necessary context
 * This ensures they render properly in the test environment
 */
export const MantineTestProvider: React.FC<MantineTestProviderProps> = ({
  children,
  colorScheme = 'light',
}) => {
  // Mock toggle function that does nothing
  const toggleColorScheme = () => {};

  return (
    <ColorSchemeProvider colorScheme={colorScheme} toggleColorScheme={toggleColorScheme}>
      <MantineProvider
        withGlobalStyles
        withNormalizeCSS
        theme={{
          colorScheme,
          // Add any theme overrides needed for tests
        }}
      >
        {children}
      </MantineProvider>
    </ColorSchemeProvider>
  );
};

/**
 * Helper function to wrap components with the MantineTestProvider
 */
export function withMantine(component: React.ReactElement) {
  return <MantineTestProvider>{component}</MantineTestProvider>;
}