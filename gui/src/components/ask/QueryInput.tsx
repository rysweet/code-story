import React, { useState } from 'react';
import {
  Card,
  Textarea,
  Button,
  Group,
  Stack,
  Text,
  Select,
  Divider,
  ActionIcon,
  Tooltip,
} from '@mantine/core';
import { IconSend, IconClearAll, IconHistory, IconDeviceFloppy } from '@tabler/icons-react';

// Example questions that can be pre-filled
const EXAMPLE_QUESTIONS = [
  'What are the main classes in the auth module?',
  'How does the ingestion pipeline work?',
  'What dependencies does the FileSystemStep have?',
  'Show me all functions that handle errors',
  'Find all classes that implement the PipelineStep interface',
];

interface QueryInputProps {
  onSubmit: (query: string) => void;
  isLoading?: boolean;
  onSaveQuery?: (query: string) => void;
  onClearHistory?: () => void;
}

/**
 * Component for natural language query input
 */
const QueryInput: React.FC<QueryInputProps> = ({
  onSubmit,
  isLoading = false,
  onSaveQuery,
  onClearHistory,
}) => {
  const [query, setQuery] = useState('');
  const [selectedExample, setSelectedExample] = useState<string | null>(null);

  // Handle question submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) {
      return;
    }
    
    onSubmit(query);
  };

  // Handle example selection
  const handleExampleSelect = (value: string | null) => {
    setSelectedExample(value);
    if (value) {
      setQuery(value);
    }
  };

  return (
    <Card shadow="sm" radius="md" p="md" withBorder>
      <form onSubmit={handleSubmit}>
        <Stack spacing="md">
          <Text weight={500} size="lg">Ask about your codebase</Text>
          
          <Textarea
            placeholder="Ask a question about your code..."
            minRows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
            autosize
          />
          
          <Group position="apart">
            <Group spacing="xs">
              <Button
                type="submit"
                leftIcon={<IconSend size={16} />}
                loading={isLoading}
                disabled={!query.trim()}
              >
                Ask Question
              </Button>
              
              <Tooltip label="Clear input">
                <ActionIcon
                  variant="outline"
                  onClick={() => setQuery('')}
                  disabled={!query.trim()}
                >
                  <IconClearAll size={16} />
                </ActionIcon>
              </Tooltip>
              
              {onSaveQuery && (
                <Tooltip label="Save query for later">
                  <ActionIcon
                    variant="outline"
                    color="blue"
                    onClick={() => onSaveQuery(query)}
                    disabled={!query.trim()}
                  >
                    <IconDeviceFloppy size={16} />
                  </ActionIcon>
                </Tooltip>
              )}
              
              {onClearHistory && (
                <Tooltip label="Clear history">
                  <ActionIcon
                    variant="outline"
                    color="red"
                    onClick={onClearHistory}
                  >
                    <IconHistory size={16} />
                  </ActionIcon>
                </Tooltip>
              )}
            </Group>
            
            <Select
              placeholder="Try an example..."
              data={EXAMPLE_QUESTIONS.map(q => ({ value: q, label: q }))}
              value={selectedExample}
              onChange={handleExampleSelect}
              clearable
              searchable
              style={{ minWidth: 250 }}
            />
          </Group>
          
          <Divider label="Tips" labelPosition="center" />
          
          <Text size="sm" color="dimmed">
            Ask questions about code structure, functionality, dependencies, or specific implementation details.
            Be specific about file paths, class names, or functionality for more accurate answers.
          </Text>
        </Stack>
      </form>
    </Card>
  );
};

export default QueryInput;