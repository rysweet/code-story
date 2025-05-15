/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';

// This is to fix the hoisting issue by making vi.mock use a factory pattern
// that returns a module with proper mock functions
vi.mock('@mantine/core', async (importOriginal) => {
  // Define a simple component factory
  const componentFactory = (name) => {
    const component = function(props) {
      return React.createElement('div', { 'data-testid': name, ...props }, props.children);
    };
    return vi.fn(component);
  };

  // Create mocks for all needed components
  return {
    TextInput: componentFactory('TextInput'),
    NumberInput: componentFactory('NumberInput'),
    Checkbox: componentFactory('Checkbox'),
    Select: componentFactory('Select'),
    MultiSelect: componentFactory('MultiSelect'),
    JsonInput: componentFactory('JsonInput'),
    Group: componentFactory('Group'),
    Stack: componentFactory('Stack'),
    Tooltip: componentFactory('Tooltip'),
    ActionIcon: componentFactory('ActionIcon'),
    Text: componentFactory('Text'),
  };
});

// Also mock the icons
vi.mock('@tabler/icons-react', async () => {
  const iconFactory = (name) => {
    return function() {
      return React.createElement('span', { 'data-testid': name });
    };
  };
  
  return {
    IconInfoCircle: iconFactory('IconInfoCircle'),
  };
});

// Now import the component
import McpParameterForm from '../McpParameterForm';

// Get references to the mocks
const mocks = vi.mocked(await import('@mantine/core'));

describe('McpParameterForm', () => {
  const mockOnChange = vi.fn();
  
  const mockParameters = {
    query: {
      type: 'string',
      title: 'Cypher Query',
      description: 'Neo4j Cypher query to execute',
      required: true,
    },
    limit: {
      type: 'integer',
      title: 'Result Limit',
      description: 'Maximum number of results to return',
      minimum: 1,
      maximum: 1000,
      default: 100,
    },
    includeMetadata: {
      type: 'boolean',
      title: 'Include Metadata',
      description: 'Whether to include node/relationship metadata',
      default: false,
    },
    resultFormat: {
      type: 'string',
      enum: ['json', 'table', 'graph'],
      title: 'Result Format',
      description: 'Format of the results',
      default: 'json',
    },
  };
  
  const mockValues = {
    query: 'MATCH (n) RETURN n LIMIT 10',
    limit: 50,
    includeMetadata: true,
    resultFormat: 'graph',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });
  
  it('should render parameter fields based on schema', () => {
    render(
      <McpParameterForm
        parameters={mockParameters}
        values={mockValues}
        onChange={mockOnChange}
      />
    );
    
    // Verify components were called
    expect(mocks.TextInput).toHaveBeenCalled();
    expect(mocks.NumberInput).toHaveBeenCalled();
    expect(mocks.Checkbox).toHaveBeenCalled();
    expect(mocks.Select).toHaveBeenCalled();
  });
  
  it('should handle empty parameters', () => {
    render(
      <McpParameterForm
        parameters={{}}
        values={{}}
        onChange={mockOnChange}
      />
    );
    
    // Check for empty state message
    expect(mocks.Text).toHaveBeenCalledWith(
      expect.objectContaining({ 
        children: 'No parameters required for this tool',
        color: 'dimmed'
      }),
      expect.anything()
    );
  });
});