import React from 'react';
import {
  TextInput,
  NumberInput,
  Checkbox,
  Select,
  MultiSelect,
  Divider,
  Text,
  Stack,
  Group,
  Title,
  Paper,
  Box,
  Switch,
  PasswordInput,
  JsonInput,
  Tooltip,
  ActionIcon,
} from '@mantine/core';
import { IconInfoCircle, IconLock } from '@tabler/icons-react';

/**
 * Props for the ConfigSchema component
 */
interface ConfigSchemaProps {
  schema: Record<string, any>;
  values: Record<string, any>;
  onChange: (path: string, value: any) => void;
  readOnly?: boolean;
}

/**
 * Component that generates form inputs based on JSON Schema definition
 */
const ConfigSchema: React.FC<ConfigSchemaProps> = ({
  schema,
  values,
  onChange,
  readOnly = false,
}) => {
  if (!schema || !schema.properties) {
    return <Text color="dimmed">No schema available</Text>;
  }

  // Group properties by their section (first part of the path)
  const groupedProperties: Record<string, Record<string, any>> = {};
  
  Object.entries(schema.properties).forEach(([key, value]) => {
    const [section, ...rest] = key.split('.');
    const propPath = rest.length > 0 ? rest.join('.') : 'default';
    
    if (!groupedProperties[section]) {
      groupedProperties[section] = {};
    }
    
    groupedProperties[section][propPath !== 'default' ? propPath : key] = { 
      ...value as object, 
      key 
    };
  });

  // Function to get the current value from the nested structure
  const getValue = (path: string) => {
    const parts = path.split('.');
    let current = values;
    
    for (const part of parts) {
      if (current === undefined || current === null) return undefined;
      current = current[part];
    }
    
    return current;
  };

  // Render form control based on schema type
  const renderControl = (
    propertyKey: string,
    propertySchema: Record<string, any>,
    path: string
  ) => {
    const currentValue = getValue(path);
    const isRequired = schema.required?.includes(path);
    const isSecret = propertySchema.format === 'password' || propertySchema.secret === true;
    
    // Common props for all form controls
    const commonProps = {
      key: path,
      label: propertySchema.title || propertyKey,
      description: propertySchema.description,
      required: isRequired,
      disabled: readOnly,
      labelProps: { style: { marginBottom: 5 } },
      style: { marginBottom: 15 },
    };
    
    // Add tooltip with info icon if there's a description
    const labelWithTooltip = propertySchema.description ? (
      <Group spacing={5} noWrap>
        {commonProps.label}
        <Tooltip label={propertySchema.description} position="top-start" withArrow>
          <ActionIcon size="xs" variant="transparent">
            <IconInfoCircle size={14} />
          </ActionIcon>
        </Tooltip>
        {isSecret && (
          <IconLock size={14} style={{ opacity: 0.6 }} />
        )}
      </Group>
    ) : (
      <Group spacing={5} noWrap>
        {commonProps.label}
        {isSecret && (
          <IconLock size={14} style={{ opacity: 0.6 }} />
        )}
      </Group>
    );

    // Handle different schema types
    switch (propertySchema.type) {
      case 'string':
        if (propertySchema.enum) {
          return (
            <Select
              {...commonProps}
              label={labelWithTooltip}
              data={propertySchema.enum.map((value: string) => ({ 
                value, 
                label: value 
              }))}
              value={currentValue || ''}
              onChange={(value) => onChange(path, value)}
              clearable={!isRequired}
            />
          );
        }
        
        if (propertySchema.format === 'password' || propertySchema.secret === true) {
          return (
            <PasswordInput
              {...commonProps}
              label={labelWithTooltip}
              value={currentValue || ''}
              onChange={(e) => onChange(path, e.target.value)}
            />
          );
        }
        
        if (propertySchema.format === 'json') {
          return (
            <JsonInput
              {...commonProps}
              label={labelWithTooltip}
              value={currentValue || ''}
              onChange={(value) => onChange(path, value)}
              formatOnBlur
              autosize
              minRows={3}
            />
          );
        }
        
        return (
          <TextInput
            {...commonProps}
            label={labelWithTooltip}
            value={currentValue || ''}
            onChange={(e) => onChange(path, e.target.value)}
          />
        );
        
      case 'integer':
      case 'number':
        return (
          <NumberInput
            {...commonProps}
            label={labelWithTooltip}
            value={currentValue || 0}
            onChange={(value) => onChange(path, value)}
            min={propertySchema.minimum}
            max={propertySchema.maximum}
            step={propertySchema.type === 'integer' ? 1 : 0.1}
          />
        );
        
      case 'boolean':
        return (
          <Switch
            {...commonProps}
            label={labelWithTooltip}
            checked={!!currentValue}
            onChange={(e) => onChange(path, e.currentTarget.checked)}
          />
        );
        
      case 'array':
        if (propertySchema.items?.enum) {
          return (
            <MultiSelect
              {...commonProps}
              label={labelWithTooltip}
              data={propertySchema.items.enum.map((value: string) => ({ 
                value, 
                label: value 
              }))}
              value={Array.isArray(currentValue) ? currentValue : []}
              onChange={(value) => onChange(path, value)}
            />
          );
        }
        
        // Default array handling (could be enhanced for nested arrays)
        return (
          <TextInput
            {...commonProps}
            label={labelWithTooltip}
            value={Array.isArray(currentValue) ? currentValue.join(', ') : ''}
            onChange={(e) => {
              const value = e.target.value.split(',').map(v => v.trim());
              onChange(path, value);
            }}
            placeholder="Comma-separated values"
          />
        );
        
      case 'object':
        // For objects, we would recursively render nested forms,
        // but for simplicity we'll use JsonInput
        return (
          <JsonInput
            {...commonProps}
            label={labelWithTooltip}
            value={currentValue ? JSON.stringify(currentValue, null, 2) : '{}'}
            onChange={(value) => {
              try {
                onChange(path, JSON.parse(value));
              } catch (e) {
                // Invalid JSON, keep the string value
                onChange(path, value);
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
            {...commonProps}
            label={labelWithTooltip}
            value={currentValue || ''}
            onChange={(e) => onChange(path, e.target.value)}
          />
        );
    }
  };

  // Render each section
  return (
    <Stack spacing="lg">
      {Object.entries(groupedProperties).map(([section, properties]) => (
        <Paper key={section} p="md" radius="md" withBorder>
          <Title order={3} mb="md">
            {section.charAt(0).toUpperCase() + section.slice(1)}
          </Title>
          
          <Divider mb="md" />
          
          <Box>
            {Object.entries(properties).map(([propKey, propSchema]) => 
              renderControl(propKey, propSchema as Record<string, any>, (propSchema as any).key)
            )}
          </Box>
        </Paper>
      ))}
    </Stack>
  );
};

export default ConfigSchema;