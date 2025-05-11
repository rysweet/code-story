import React from 'react';
import {
  TextInput,
  NumberInput,
  Checkbox,
  Select,
  MultiSelect,
  Stack,
  Text,
  Tooltip,
  Group,
  ActionIcon,
  JsonInput,
} from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';

interface McpParameterFormProps {
  parameters: Record<string, any>;
  values: Record<string, any>;
  onChange: (name: string, value: any) => void;
}

/**
 * Component for rendering dynamic parameter form for MCP tools
 */
const McpParameterForm: React.FC<McpParameterFormProps> = ({
  parameters,
  values,
  onChange,
}) => {
  if (!parameters || Object.keys(parameters).length === 0) {
    return <Text color="dimmed">No parameters required for this tool</Text>;
  }

  // Render a parameter based on its schema
  const renderParameter = (name: string, schema: any) => {
    const value = values[name];
    const required = schema.required || false;
    
    // Common props for all form controls - without 'key' which needs to be passed directly
    const commonProps = {
      label: (
        <Group spacing={5} noWrap>
          {schema.title || name}
          {schema.description && (
            <Tooltip label={schema.description} position="top-start" withArrow>
              <ActionIcon size="xs" variant="transparent">
                <IconInfoCircle size={14} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
      ),
      required,
      style: { marginBottom: 15 },
    };
    
    // Handle different schema types
    switch (schema.type) {
      case 'string':
        if (schema.enum) {
          return (
            <Select
              key={name}
              {...commonProps}
              data={schema.enum.map((value: string) => ({ 
                value, 
                label: value 
              }))}
              value={value || ''}
              onChange={(value) => onChange(name, value)}
              clearable={!required ? "true" : undefined}
            />
          );
        }
        
        if (schema.format === 'json') {
          return (
            <JsonInput
              key={name}
              {...commonProps}
              value={value || ''}
              onChange={(value) => onChange(name, value)}
              formatOnBlur
              autosize
              minRows={3}
            />
          );
        }
        
        return (
          <TextInput
            key={name}
            {...commonProps}
            value={value || ''}
            onChange={(e) => onChange(name, e.target.value)}
          />
        );
        
      case 'integer':
      case 'number':
        return (
          <NumberInput
            key={name}
            {...commonProps}
            value={value || 0}
            onChange={(value) => onChange(name, value)}
            min={schema.minimum}
            max={schema.maximum}
            step={schema.type === 'integer' ? 1 : 0.1}
          />
        );
        
      case 'boolean':
        return (
          <Checkbox
            key={name}
            {...commonProps}
            label={schema.title || name}
            checked={!!value}
            onChange={(e) => onChange(name, e.currentTarget.checked)}
          />
        );
        
      case 'array':
        if (schema.items?.enum) {
          return (
            <MultiSelect
              key={name}
              {...commonProps}
              data={schema.items.enum.map((value: string) => ({ 
                value, 
                label: value 
              }))}
              value={Array.isArray(value) ? value : []}
              onChange={(value) => onChange(name, value)}
            />
          );
        }
        
        // Default array handling
        return (
          <TextInput
            key={name}
            {...commonProps}
            value={Array.isArray(value) ? value.join(', ') : ''}
            onChange={(e) => {
              const value = e.target.value.split(',').map(v => v.trim());
              onChange(name, value);
            }}
            placeholder="Comma-separated values"
          />
        );
        
      case 'object':
        return (
          <JsonInput
            key={name}
            {...commonProps}
            value={value ? JSON.stringify(value, null, 2) : '{}'}
            onChange={(value) => {
              try {
                onChange(name, JSON.parse(value));
              } catch (e) {
                // Invalid JSON, keep the string value
                onChange(name, value);
              }
            }}
            formatOnBlur
            autosize
            minRows={3}
          />
        );
        
      default:
        return (
          <TextInput
            key={name}
            {...commonProps}
            value={value || ''}
            onChange={(e) => onChange(name, e.target.value)}
          />
        );
    }
  };

  return (
    <Stack spacing="md">
      {Object.entries(parameters).map(([name, schema]) => 
        renderParameter(name, schema)
      )}
    </Stack>
  );
};

export default McpParameterForm;