import React, { useEffect } from 'react';
import { Box, Title, Text, Stack, Space } from '@mantine/core';
import { useDispatch } from 'react-redux';
import { setActivePage } from '../store/slices/uiSlice';
import { ConfigEditor, DatabaseManager } from '../components/config';

/**
 * ConfigPage component for managing configuration settings
 */
const ConfigPage: React.FC = () => {
  const dispatch = useDispatch();

  // Set active page when component mounts
  useEffect(() => {
    dispatch(setActivePage('config'));
  }, [dispatch]);

  return (
    <Box p="md">
      <Stack spacing="md">
        <Title order={2}>Configuration</Title>

        <Text color="dimmed">
          Manage the configuration settings for the Code Story service.
          Changes are saved to the .env or .codestory.toml file on the server.
        </Text>

        <ConfigEditor />
        
        <Space h="md" />
        
        <DatabaseManager />
      </Stack>
    </Box>
  );
};

export default ConfigPage;