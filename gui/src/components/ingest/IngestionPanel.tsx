import React, { useState } from 'react';
import { 
  Card, 
  TextInput, 
  Button, 
  Group, 
  Stack, 
  Text, 
  Checkbox,
  JsonInput,
  Alert,
  Divider
} from '@mantine/core';
import { IconFolderOpen, IconPlay, IconX } from '@tabler/icons-react';
import { useStartIngestionMutation } from '../../store';

interface IngestionPanelProps {
  onStarted?: (jobId: string) => void;
}

/**
 * Component for starting new ingestion jobs
 */
const IngestionPanel: React.FC<IngestionPanelProps> = ({ onStarted }) => {
  const [repositoryPath, setRepositoryPath] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [optionsText, setOptionsText] = useState('{\n  "max_depth": 10,\n  "ignore_patterns": [".git", "node_modules", "dist"]\n}');
  const [optionsError, setOptionsError] = useState<string | null>(null);
  
  const [startIngestion, { isLoading, error }] = useStartIngestionMutation();
  
  // Parse options JSON
  const parseOptions = (): Record<string, any> | null => {
    if (!showAdvanced) return null;
    
    try {
      const options = JSON.parse(optionsText);
      setOptionsError(null);
      return options;
    } catch (err) {
      setOptionsError('Invalid JSON format');
      return null;
    }
  };
  
  // Start an ingestion job
  const handleStartIngestion = async () => {
    if (!repositoryPath.trim()) {
      return;
    }
    
    const options = parseOptions();
    if (showAdvanced && !options) {
      return;
    }
    
    try {
      const result = await startIngestion({ 
        repository_path: repositoryPath,
        options 
      }).unwrap();
      
      if (onStarted) {
        onStarted(result.job_id);
      }
    } catch (err) {
      console.error('Failed to start ingestion:', err);
    }
  };
  
  return (
    <Card shadow="sm" radius="md" p="md" withBorder>
      <Stack spacing="md">
        <Text weight={500} size="lg">Start New Ingestion</Text>
        
        <TextInput
          required
          label="Repository Path"
          placeholder="Enter absolute path to the repository"
          value={repositoryPath}
          onChange={(e) => setRepositoryPath(e.target.value)}
          rightSection={
            <Button 
              compact 
              variant="subtle" 
              p={0} 
              w={24} 
              h={24}
              onClick={() => {
                // In a real implementation, this would open a file dialog
                // For now, just set a sample path
                setRepositoryPath('/Users/example/projects/my-repo');
              }}
            >
              <IconFolderOpen size={16} />
            </Button>
          }
        />
        
        <Checkbox
          label="Advanced Options"
          checked={showAdvanced}
          onChange={(e) => setShowAdvanced(e.currentTarget.checked)}
        />
        
        {showAdvanced && (
          <>
            <JsonInput
              label="Options (JSON)"
              placeholder="Enter options as JSON"
              validationError="Invalid JSON"
              formatOnBlur
              autosize
              minRows={5}
              value={optionsText}
              onChange={setOptionsText}
              error={optionsError}
            />
            
            <Divider label="Available Options" labelPosition="center" />
            
            <Stack spacing="xs">
              <Text size="sm" color="dimmed">
                • max_depth: Maximum directory depth to traverse
              </Text>
              <Text size="sm" color="dimmed">
                • ignore_patterns: List of glob patterns to ignore
              </Text>
              <Text size="sm" color="dimmed">
                • steps: List of specific steps to run, e.g. ["filesystem", "summarizer"]
              </Text>
              <Text size="sm" color="dimmed">
                • force: Set to true to force reingestion of all files
              </Text>
            </Stack>
          </>
        )}
        
        {error && (
          <Alert color="red" title="Error" icon={<IconX size={16} />} withCloseButton>
            {JSON.stringify(error)}
          </Alert>
        )}
        
        <Group position="right">
          <Button
            leftIcon={<IconPlay size={16} />}
            onClick={handleStartIngestion}
            loading={isLoading}
            disabled={!repositoryPath.trim() || (showAdvanced && !!optionsError)}
          >
            Start Ingestion
          </Button>
        </Group>
      </Stack>
    </Card>
  );
};

export default IngestionPanel;