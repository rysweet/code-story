import React from 'react';
import { Box, Group, Title, Button } from '@mantine/core';

/**
 * Header component for the application
 */
const Header: React.FC = () => {
  return (
    <Box
      py="md"
      px="lg"
      sx={(theme) => ({
        borderBottom: `1px solid ${theme.colors.gray[3]}`,
        backgroundColor: theme.white,
      })}
    >
      <Group position="apart">
        <Title order={3}>Code Story</Title>
        <Group>
          <Button variant="light">Service Status</Button>
        </Group>
      </Group>
    </Box>
  );
};

export default Header;