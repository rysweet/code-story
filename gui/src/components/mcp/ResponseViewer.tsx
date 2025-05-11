import React, { useState } from 'react';
import {
  Stack,
  Text,
  Alert,
  Paper,
  Tabs,
  CopyButton,
  ActionIcon,
  Tooltip,
  Code,
  ScrollArea,
} from '@mantine/core';
import { IconCode, IconBrandJson, IconClipboard, IconCheck } from '@tabler/icons-react';
import { ToolResponse } from '../../store';

// Helper function to syntax highlight JSON
const formatJson = (json: any) => {
  try {
    if (typeof json === 'string') {
      json = JSON.parse(json);
    }
    return JSON.stringify(json, null, 2);
  } catch (e) {
    return String(json);
  }
};

interface ResponseViewerProps {
  response: ToolResponse;
}

/**
 * Component for displaying tool call responses with syntax highlighting
 */
const ResponseViewer: React.FC<ResponseViewerProps> = ({ response }) => {
  const [activeTab, setActiveTab] = useState<string | null>('formatted');
  const formattedResponse = formatJson(response.result);
  
  // If there's an error in the response
  if (response.error) {
    return (
      <Alert color="red" title="Error">
        {response.error}
      </Alert>
    );
  }
  
  return (
    <Stack spacing="md">
      <Tabs value={activeTab} onTabChange={setActiveTab}>
        <Tabs.List>
          <Tabs.Tab value="formatted" icon={<IconBrandJson size={14} />}>
            Formatted JSON
          </Tabs.Tab>
          <Tabs.Tab value="raw" icon={<IconCode size={14} />}>
            Raw Response
          </Tabs.Tab>
        </Tabs.List>
        
        <Tabs.Panel value="formatted" pt="md">
          <Paper p="md" withBorder>
            <Stack spacing="xs">
              <Group position="right">
                <CopyButton value={formattedResponse} timeout={2000}>
                  {({ copied, copy }) => (
                    <Tooltip label={copied ? 'Copied' : 'Copy'} withArrow>
                      <ActionIcon color={copied ? 'teal' : 'gray'} onClick={copy}>
                        {copied ? <IconCheck size={16} /> : <IconClipboard size={16} />}
                      </ActionIcon>
                    </Tooltip>
                  )}
                </CopyButton>
              </Group>
              
              <ScrollArea h={300}>
                <Code block>
                  {formattedResponse}
                </Code>
              </ScrollArea>
            </Stack>
          </Paper>
        </Tabs.Panel>
        
        <Tabs.Panel value="raw" pt="md">
          <Paper p="md" withBorder>
            <Stack spacing="xs">
              <Group position="right">
                <CopyButton value={JSON.stringify(response.result)} timeout={2000}>
                  {({ copied, copy }) => (
                    <Tooltip label={copied ? 'Copied' : 'Copy'} withArrow>
                      <ActionIcon color={copied ? 'teal' : 'gray'} onClick={copy}>
                        {copied ? <IconCheck size={16} /> : <IconClipboard size={16} />}
                      </ActionIcon>
                    </Tooltip>
                  )}
                </CopyButton>
              </Group>
              
              <ScrollArea h={300}>
                <Code block>
                  {JSON.stringify(response.result)}
                </Code>
              </ScrollArea>
            </Stack>
          </Paper>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
};

export default ResponseViewer;