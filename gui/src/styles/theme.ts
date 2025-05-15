import { MantineThemeOverride } from '@mantine/core';

/**
 * Mantine theme configuration for Code Story
 */
export const theme: MantineThemeOverride = {
  colorScheme: 'light',
  fontFamily: 'Inter, system-ui, sans-serif',
  primaryColor: 'blue',
  headings: {
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  components: {
    Button: {
      defaultProps: {
        radius: 'md',
      },
    },
    Card: {
      defaultProps: {
        radius: 'md',
        shadow: 'sm',
      },
    },
  },
};