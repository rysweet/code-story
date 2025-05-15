import React from 'react';
import {
  Card,
  Text,
  Stack,
  Group,
  Loader,
  Alert,
  ScrollArea,
  CopyButton,
  ActionIcon,
  Tooltip,
  TypographyStylesProvider,
  Code,
  Tabs,
} from '@mantine/core';
import {
  IconCheck,
  IconClipboard,
  IconAlertCircle,
  IconMarkdown,
  IconCode,
  IconGraph,
} from '@tabler/icons-react';
import { formatDate } from '../../utils/formatters';

interface AnswerDisplayProps {
  question: string;
  answer: string | null;
  isLoading?: boolean;
  error?: string | null;
  timestamp?: string;
  relatedNodes?: Array<{
    id: string;
    name: string;
    type: string;
    path?: string;
  }>;
}

/**
 * Component for displaying natural language query answers with formatting
 */
const AnswerDisplay: React.FC<AnswerDisplayProps> = ({
  question,
  answer,
  isLoading = false,
  error = null,
  timestamp = new Date().toISOString(),
  relatedNodes = [],
}) => {
  const [activeTab, setActiveTab] = React.useState<string | null>('formatted');
  
  // Show loading state
  if (isLoading) {
    return (
      <Card shadow="sm" radius="md" p="md" withBorder>
        <Stack spacing="md" align="center" py="xl">
          <Loader size="lg" />
          <Text>Processing your question...</Text>
        </Stack>
      </Card>
    );
  }
  
  // Show error state
  if (error) {
    return (
      <Card shadow="sm" radius="md" p="md" withBorder>
        <Alert 
          icon={<IconAlertCircle size={16} />} 
          title="Error" 
          color="red"
        >
          {error}
        </Alert>
      </Card>
    );
  }
  
  // Empty answer state
  if (!answer) {
    return null;
  }
  
  return (
    <Card shadow="sm" radius="md" p="md" withBorder>
      <Stack spacing="md">
        <Group position="apart">
          <Text weight={500} size="lg">Answer</Text>
          <Text size="xs" color="dimmed">{formatDate(timestamp)}</Text>
        </Group>
        
        <Alert color="blue" variant="light">
          <Text weight={500}>{question}</Text>
        </Alert>
        
        <Tabs value={activeTab} onTabChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="formatted" icon={<IconMarkdown size={14} />}>
              Formatted
            </Tabs.Tab>
            <Tabs.Tab value="raw" icon={<IconCode size={14} />}>
              Raw Text
            </Tabs.Tab>
            {relatedNodes.length > 0 && (
              <Tabs.Tab value="related" icon={<IconGraph size={14} />}>
                Related Nodes
              </Tabs.Tab>
            )}
          </Tabs.List>
          
          <Tabs.Panel value="formatted" pt="md">
            <Group position="right" mb="xs">
              <CopyButton value={answer} timeout={2000}>
                {({ copied, copy }) => (
                  <Tooltip label={copied ? 'Copied' : 'Copy'} withArrow>
                    <ActionIcon color={copied ? 'teal' : 'gray'} onClick={copy}>
                      {copied ? <IconCheck size={16} /> : <IconClipboard size={16} />}
                    </ActionIcon>
                  </Tooltip>
                )}
              </CopyButton>
            </Group>
            
            <ScrollArea h={400}>
              <TypographyStylesProvider>
                <div dangerouslySetInnerHTML={{ __html: formatMarkdown(answer) }} />
              </TypographyStylesProvider>
            </ScrollArea>
          </Tabs.Panel>
          
          <Tabs.Panel value="raw" pt="md">
            <Group position="right" mb="xs">
              <CopyButton value={answer} timeout={2000}>
                {({ copied, copy }) => (
                  <Tooltip label={copied ? 'Copied' : 'Copy'} withArrow>
                    <ActionIcon color={copied ? 'teal' : 'gray'} onClick={copy}>
                      {copied ? <IconCheck size={16} /> : <IconClipboard size={16} />}
                    </ActionIcon>
                  </Tooltip>
                )}
              </CopyButton>
            </Group>
            
            <ScrollArea h={400}>
              <Code block>{answer}</Code>
            </ScrollArea>
          </Tabs.Panel>
          
          {relatedNodes.length > 0 && (
            <Tabs.Panel value="related" pt="md">
              <Stack spacing="md">
                <Text weight={500}>Related Elements ({relatedNodes.length})</Text>
                
                <ScrollArea h={400}>
                  <Stack spacing="xs">
                    {relatedNodes.map((node) => (
                      <Card key={node.id} p="xs" withBorder>
                        <Group position="apart">
                          <div>
                            <Text weight={500}>{node.name}</Text>
                            <Group spacing={5}>
                              <Text size="xs" color="dimmed">{node.type}</Text>
                              {node.path && (
                                <Text size="xs" color="dimmed" style={{ wordBreak: 'break-all' }}>
                                  {node.path}
                                </Text>
                              )}
                            </Group>
                          </div>
                        </Group>
                      </Card>
                    ))}
                  </Stack>
                </ScrollArea>
              </Stack>
            </Tabs.Panel>
          )}
        </Tabs>
      </Stack>
    </Card>
  );
};

// Helper function to format markdown
// In a real implementation, this would use a library like marked or remark
const formatMarkdown = (markdown: string): string => {
  const formatted = markdown
    // Convert headers
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    // Convert code blocks
    .replace(/```(\w+)?\n([\s\S]*?)\n```/gm, '<pre><code>$2</code></pre>')
    // Convert inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Convert bold
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Convert italics
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Convert line breaks
    .replace(/\n/g, '<br />');

  return formatted;
};

export default AnswerDisplay;