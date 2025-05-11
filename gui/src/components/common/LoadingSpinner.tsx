import React from 'react';
import { Center, Loader, Text, Stack } from '@mantine/core';

/**
 * Loading spinner component with optional message
 */
const LoadingSpinner: React.FC<{ message?: string }> = ({ message = 'Loading...' }) => {
  return (
    <Center style={{ height: '100%', minHeight: 200 }}>
      <Stack align="center" spacing="xs">
        <Loader size="md" />
        <Text size="sm" color="dimmed">{message}</Text>
      </Stack>
    </Center>
  );
};

export default LoadingSpinner;