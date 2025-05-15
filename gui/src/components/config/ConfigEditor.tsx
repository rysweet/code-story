import React, { useState, useEffect } from 'react';
import {
  Paper,
  Button,
  Group,
  Text,
  Stack,
  Alert,
  Loader,
  Checkbox,
  Tabs,
  JsonInput,
  Divider,
} from '@mantine/core';
import { IconDeviceFloppy, IconRefresh, IconX, IconCheck, IconAlertCircle, IconCode } from '@tabler/icons-react';
import { useGetConfigQuery, useGetConfigSchemaQuery, useUpdateConfigMutation } from '../../store/api/configApi';
import ConfigSchema from './ConfigSchema';

/**
 * ConfigEditor component for editing configuration
 */
const ConfigEditor: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string | null>('form');
  const [includeSensitive, setIncludeSensitive] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [jsonValue, setJsonValue] = useState('');
  const [jsonError, setJsonError] = useState<string | null>(null);
  
  // RTK Query hooks
  const { data: config, isLoading: isLoadingConfig, error: configError, refetch: refetchConfig } = 
    useGetConfigQuery(includeSensitive);
  const { data: schema, isLoading: isLoadingSchema, error: schemaError } = useGetConfigSchemaQuery();
  const [updateConfig, { isLoading: isSaving, error: saveError, isSuccess: isSaveSuccess }] = useUpdateConfigMutation();
  
  // When config data changes, update the form values and JSON
  useEffect(() => {
    if (config) {
      setFormValues(config);
      setJsonValue(JSON.stringify(config, null, 2));
    }
  }, [config]);
  
  // Handle form field changes
  const handleChange = (path: string, value: any) => {
    // Update the form values with the nested path
    setFormValues(prev => {
      const newValues = { ...prev };
      const parts = path.split('.');
      let current = newValues;
      
      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        if (!current[part]) {
          current[part] = {};
        }
        current = current[part];
      }
      
      current[parts[parts.length - 1]] = value;
      return newValues;
    });
    
    setHasChanges(true);
    
    // Update JSON view if that tab is active
    setJsonValue(JSON.stringify(formValues, null, 2));
  };
  
  // Handle JSON tab changes
  const handleJsonChange = (value: string) => {
    setJsonValue(value);
    setJsonError(null);
    
    try {
      const parsed = JSON.parse(value);
      setFormValues(parsed);
      setHasChanges(true);
    } catch (e) {
      setJsonError('Invalid JSON format');
    }
  };
  
  // Save configuration changes
  const handleSave = async () => {
    try {
      if (activeTab === 'json' && jsonError) {
        return;
      }
      
      await updateConfig(formValues).unwrap();
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save configuration:', error);
    }
  };
  
  // Refresh configuration
  const handleRefresh = () => {
    refetchConfig();
    setHasChanges(false);
  };
  
  // Toggle sensitive data
  const handleToggleSensitive = (checked: boolean) => {
    setIncludeSensitive(checked);
  };
  
  // Show loading state
  if (isLoadingConfig || isLoadingSchema) {
    return (
      <Paper p="md" radius="md" withBorder>
        <Stack align="center" py="xl">
          <Loader />
          <Text>Loading configuration...</Text>
        </Stack>
      </Paper>
    );
  }
  
  // Show error state
  if (configError || schemaError) {
    return (
      <Paper p="md" radius="md" withBorder>
        <Alert 
          icon={<IconAlertCircle size={16} />} 
          title="Error loading configuration" 
          color="red"
        >
          {configError 
            ? `Failed to load configuration: ${JSON.stringify(configError)}`
            : `Failed to load schema: ${JSON.stringify(schemaError)}`
          }
        </Alert>
        <Button mt="md" onClick={handleRefresh} leftIcon={<IconRefresh size={16} />}>
          Retry
        </Button>
      </Paper>
    );
  }
  
  return (
    <Paper p="md" radius="md" withBorder>
      <Stack spacing="md">
        {/* Controls */}
        <Group position="apart">
          <Group>
            <Button
              color={hasChanges ? 'blue' : 'gray'}
              onClick={handleSave}
              leftIcon={<IconDeviceFloppy size={16} />}
              loading={isSaving}
              disabled={!hasChanges || (activeTab === 'json' && !!jsonError)}
            >
              Save Changes
            </Button>
            
            <Button
              variant="outline"
              onClick={handleRefresh}
              leftIcon={<IconRefresh size={16} />}
              disabled={isSaving}
            >
              Refresh
            </Button>
          </Group>
          
          <Checkbox
            label="Show sensitive values"
            checked={includeSensitive}
            onChange={(e) => handleToggleSensitive(e.currentTarget.checked)}
          />
        </Group>
        
        {/* Success/Error messages */}
        {isSaveSuccess && (
          <Alert 
            icon={<IconCheck size={16} />} 
            title="Configuration saved" 
            color="green"
            withCloseButton
          >
            Your configuration changes have been saved successfully.
          </Alert>
        )}
        
        {saveError && (
          <Alert 
            icon={<IconX size={16} />} 
            title="Error saving configuration" 
            color="red"
            withCloseButton
          >
            {JSON.stringify(saveError)}
          </Alert>
        )}
        
        <Divider />
        
        {/* Tabs for form and JSON views */}
        <Tabs value={activeTab} onTabChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="form" icon={<IconCheck size={16} />}>
              Form Editor
            </Tabs.Tab>
            <Tabs.Tab value="json" icon={<IconCode size={16} />}>
              JSON Editor
            </Tabs.Tab>
          </Tabs.List>
          
          <Tabs.Panel value="form" pt="md">
            {schema && formValues && (
              <ConfigSchema
                schema={schema}
                values={formValues}
                onChange={handleChange}
              />
            )}
          </Tabs.Panel>
          
          <Tabs.Panel value="json" pt="md">
            <JsonInput
              value={jsonValue}
              onChange={handleJsonChange}
              minRows={20}
              formatOnBlur
              autosize
              error={jsonError}
              withAsterisk
            />
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Paper>
  );
};

export default ConfigEditor;