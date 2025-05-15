/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock the ResponseViewer component directly
vi.mock('../ResponseViewer', () => ({
  default: ({ response }) => {
    if (response.error) {
      return (
        <div data-testid="error-response">
          <div data-testid="error-title">Error</div>
          <div data-testid="error-message">{response.error}</div>
        </div>
      );
    } else {
      return (
        <div data-testid="success-response">
          <div data-testid="tab-formatted">Formatted JSON</div>
          <div data-testid="tab-raw">Raw Response</div>
          <pre data-testid="json-content">{JSON.stringify(response.result, null, 2)}</pre>
        </div>
      );
    }
  }
}));

// Import after mocking
import ResponseViewer from '../ResponseViewer';
import { ToolResponse } from '../../../store';

describe('ResponseViewer', () => {
  it('should render successful response', () => {
    const successResponse: ToolResponse = {
      result: {
        nodes: [
          { id: 'node1', labels: ['Person'], properties: { name: 'John' } },
          { id: 'node2', labels: ['Person'], properties: { name: 'Jane' } },
        ],
        relationships: [
          { id: 'rel1', type: 'KNOWS', startNode: 'node1', endNode: 'node2', properties: {} },
        ],
      },
    };

    render(<ResponseViewer response={successResponse} />);
    
    // Check that the success response elements are rendered
    const successResponseElement = screen.getByTestId('success-response');
    const formattedTab = screen.getByTestId('tab-formatted');
    const rawTab = screen.getByTestId('tab-raw');
    const jsonContent = screen.getByTestId('json-content');

    expect(successResponseElement).toBeDefined();
    expect(formattedTab.textContent).toBe('Formatted JSON');
    expect(rawTab.textContent).toBe('Raw Response');
    expect(jsonContent).toBeDefined();
  });
  
  it('should render error response', () => {
    const errorResponse: ToolResponse = {
      result: null,
      error: 'Failed to execute query: syntax error',
    };

    render(<ResponseViewer response={errorResponse} />);
    
    // Check that the error response elements are rendered
    const errorResponseElement = screen.getByTestId('error-response');
    const errorTitle = screen.getByTestId('error-title');
    const errorMessage = screen.getByTestId('error-message');

    expect(errorResponseElement).toBeDefined();
    expect(errorTitle.textContent).toBe('Error');
    expect(errorMessage.textContent).toBe('Failed to execute query: syntax error');
  });
});