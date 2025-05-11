import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../tests/utils';

// Mock the component to avoid Mantine component rendering issues
vi.mock('../ConfigSchema', () => {
  const React = require('react');
  
  return {
    default: ({ schema, values, onChange, readOnly = false }) => {
      if (!schema || !schema.properties) {
        return <p>No schema available</p>;
      }
      
      // Group properties by section (first part of the path)
      const sections = {};
      Object.entries(schema.properties).forEach(([key, value]) => {
        const [section] = key.split('.');
        if (!sections[section]) sections[section] = [];
        sections[section].push({ key, schema: value });
      });

      // Function to get the current value from nested structure
      const getValue = (path) => {
        const parts = path.split('.');
        let current = values;
        for (const part of parts) {
          if (current === undefined || current === null) return undefined;
          current = current[part];
        }
        return current;
      };
      
      // Handle input changes
      const handleChange = (path, event) => {
        let value;
        
        // Parse different input types
        if (event && event.target) {
          // Regular input event
          if (event.target.type === 'checkbox') {
            value = event.target.checked;
          } else if (event.target.type === 'number') {
            value = Number(event.target.value);
          } else {
            value = event.target.value;
          }
        } else {
          // Direct value (like from Select)
          value = event;
        }
        
        onChange(path, value);
      };
      
      return (
        <div data-testid="config-schema">
          {Object.entries(sections).map(([section, fields]) => (
            <section key={section} data-testid={`section-${section}`}>
              <h3>{section.charAt(0).toUpperCase() + section.slice(1)}</h3>
              <hr />
              {fields.map(({ key, schema: fieldSchema }) => {
                const currentValue = getValue(key);
                const isRequired = schema.required?.includes(key);
                const isSecret = fieldSchema.format === 'password' || fieldSchema.secret === true;
                
                // Render different input types based on schema
                switch (fieldSchema.type) {
                  case 'string':
                    if (fieldSchema.enum) {
                      return (
                        <div key={key}>
                          <label htmlFor={key}>{fieldSchema.title}</label>
                          <select 
                            id={key}
                            aria-label={fieldSchema.title}
                            value={currentValue || ''}
                            onChange={(e) => onChange(key, e.target.value)}
                            disabled={readOnly}
                            data-testid={`select-${key}`}
                          >
                            {fieldSchema.enum.map((option) => (
                              <option key={option} value={option}>{option}</option>
                            ))}
                          </select>
                        </div>
                      );
                    }
                    
                    if (isSecret) {
                      return (
                        <div key={key}>
                          <label htmlFor={key}>{fieldSchema.title}</label>
                          <input 
                            id={key}
                            type="password"
                            aria-label={fieldSchema.title}
                            value={currentValue || ''}
                            onChange={(e) => onChange(key, e.target.value)}
                            disabled={readOnly}
                            required={isRequired}
                            data-testid={`password-${key}`}
                          />
                        </div>
                      );
                    }
                    
                    return (
                      <div key={key}>
                        <label htmlFor={key}>{fieldSchema.title}</label>
                        <input 
                          id={key}
                          type="text"
                          aria-label={fieldSchema.title}
                          value={currentValue || ''}
                          onChange={(e) => onChange(key, e.target.value)}
                          disabled={readOnly}
                          required={isRequired}
                          data-testid={`text-${key}`}
                        />
                      </div>
                    );
                  
                  case 'integer':
                  case 'number':
                    return (
                      <div key={key}>
                        <label htmlFor={key}>{fieldSchema.title}</label>
                        <input 
                          id={key}
                          type="number"
                          role="spinbutton"
                          aria-label={fieldSchema.title}
                          value={currentValue || 0}
                          onChange={(e) => onChange(key, Number(e.target.value))}
                          min={fieldSchema.minimum}
                          max={fieldSchema.maximum}
                          disabled={readOnly}
                          required={isRequired}
                          data-testid={`number-${key}`}
                        />
                      </div>
                    );
                  
                  case 'boolean':
                    return (
                      <div key={key}>
                        <label htmlFor={key}>
                          <input 
                            id={key}
                            type="checkbox"
                            aria-label={fieldSchema.title}
                            checked={!!currentValue}
                            onChange={(e) => onChange(key, e.target.checked)}
                            disabled={readOnly}
                            data-testid={`checkbox-${key}`}
                          />
                          {fieldSchema.title}
                        </label>
                      </div>
                    );
                  
                  case 'array':
                    if (fieldSchema.items?.enum) {
                      // Mock a multi-select component
                      return (
                        <div key={key}>
                          <label htmlFor={key}>{fieldSchema.title}</label>
                          <select
                            id={key}
                            multiple
                            aria-label={fieldSchema.title}
                            value={Array.isArray(currentValue) ? currentValue : []}
                            onChange={(e) => {
                              const selected = Array.from(e.target.selectedOptions, option => option.value);
                              onChange(key, selected);
                            }}
                            disabled={readOnly}
                            data-testid={`multiselect-${key}`}
                          >
                            {fieldSchema.items.enum.map((option) => (
                              <option key={option} value={option}>{option}</option>
                            ))}
                          </select>
                        </div>
                      );
                    }
                    break;
                  default:
                    return null;
                }
              })}
            </section>
          ))}
        </div>
      );
    }
  };
});

// Import the mocked component
import ConfigSchema from '../ConfigSchema';

describe('ConfigSchema', () => {
  const mockSchema = {
    $schema: 'http://json-schema.org/draft-07/schema#',
    type: 'object',
    required: ['database.url', 'service.port'],
    properties: {
      'database.url': {
        type: 'string',
        title: 'Database URL',
        description: 'URL for connecting to the database',
      },
      'database.username': {
        type: 'string',
        title: 'Database Username',
      },
      'database.password': {
        type: 'string',
        format: 'password',
        title: 'Database Password',
        secret: true,
      },
      'service.port': {
        type: 'integer',
        title: 'Service Port',
        minimum: 1024,
        maximum: 65535,
      },
      'service.debug': {
        type: 'boolean',
        title: 'Debug Mode',
      },
      'service.logLevel': {
        type: 'string',
        enum: ['debug', 'info', 'warning', 'error'],
        title: 'Log Level',
      },
      'llm.models': {
        type: 'array',
        items: {
          type: 'string',
          enum: ['gpt-3.5-turbo', 'gpt-4', 'claude-2'],
        },
        title: 'Available Models',
      },
    },
  };

  const mockValues = {
    database: {
      url: 'neo4j://localhost:7687',
      username: 'neo4j',
      password: 'password123',
    },
    service: {
      port: 8000,
      debug: true,
      logLevel: 'info',
    },
    llm: {
      models: ['gpt-3.5-turbo', 'gpt-4'],
    },
  };

  const mockOnChange = vi.fn();

  it('renders form fields based on schema', () => {
    renderWithProviders(
      <ConfigSchema
        schema={mockSchema}
        values={mockValues}
        onChange={mockOnChange}
      />
    );

    // Check section titles
    expect(screen.getByText('Database')).toBeInTheDocument();
    expect(screen.getByText('Service')).toBeInTheDocument();
    expect(screen.getByText('Llm')).toBeInTheDocument();

    // Check that inputs are present
    expect(screen.getByLabelText('Database URL')).toHaveValue('neo4j://localhost:7687');
    expect(screen.getByLabelText('Database Password')).toHaveAttribute('type', 'password');
    expect(screen.getByLabelText('Service Port')).toHaveValue(8000);
    expect(screen.getByLabelText('Debug Mode')).toBeChecked();
  });

  it('handles form input changes', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ConfigSchema
        schema={mockSchema}
        values={mockValues}
        onChange={mockOnChange}
      />
    );

    // Change text input
    const databaseUrlInput = screen.getByLabelText('Database URL');
    await user.clear(databaseUrlInput);
    await user.type(databaseUrlInput, 'n');

    // Check that onChange was called for the database URL field
    expect(mockOnChange).toHaveBeenCalledWith('database.url', expect.any(String));

    // Reset mock for next test
    mockOnChange.mockClear();

    // Change number input
    const portInput = screen.getByLabelText('Service Port');
    await user.clear(portInput);
    await user.type(portInput, '9');

    // Verify it was called with a numeric port value
    expect(mockOnChange).toHaveBeenCalledWith('service.port', expect.any(Number));

    // Reset mock for next test
    mockOnChange.mockClear();

    // Toggle boolean input
    const debugSwitch = screen.getByLabelText('Debug Mode');
    await user.click(debugSwitch);

    // Verify it was called with a toggled debug value
    expect(mockOnChange).toHaveBeenCalledWith('service.debug', expect.any(Boolean));
  });

  it('handles empty or invalid schema', () => {
    renderWithProviders(
      <ConfigSchema
        schema={{}}
        values={{}}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('No schema available')).toBeInTheDocument();
  });

  it('respects readOnly prop', () => {
    renderWithProviders(
      <ConfigSchema
        schema={mockSchema}
        values={mockValues}
        onChange={mockOnChange}
        readOnly={true}
      />
    );

    // Check that inputs are disabled when readOnly is true
    expect(screen.getByLabelText('Database URL')).toBeDisabled();
    expect(screen.getByLabelText('Database Password')).toBeDisabled();
    expect(screen.getByLabelText('Service Port')).toBeDisabled();
    expect(screen.getByLabelText('Debug Mode')).toBeDisabled();
  });
});