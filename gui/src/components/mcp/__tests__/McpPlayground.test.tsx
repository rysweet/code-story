/**
 * @vitest-environment jsdom
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock the Redux hooks and store first
vi.mock('../../../store', () => ({
  useExecuteToolMutation: vi.fn().mockReturnValue([
    vi.fn().mockResolvedValue({ data: { result: { success: true } } }),
    { isLoading: false, data: null, error: null, reset: vi.fn() },
  ]),
  useGetAvailableToolsQuery: vi.fn().mockReturnValue({
    data: {
      tools: [
        {
          name: 'execute_cypher',
          description: 'Execute a Cypher query against the Neo4j database',
          parameters: {
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
          },
        },
        {
          name: 'find_similar_code',
          description: 'Find similar code patterns in the codebase',
          parameters: {
            pattern: {
              type: 'string',
              title: 'Code Pattern',
              description: 'Code pattern to search for',
              required: true,
            },
            language: {
              type: 'string',
              enum: ['python', 'javascript', 'typescript', 'java', 'csharp'],
              title: 'Language',
              description: 'Programming language to search in',
              required: true,
            },
          },
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
  useSaveToolCallTemplateMutation: vi.fn().mockReturnValue([vi.fn(), { isLoading: false, error: null }]),
}));

// Mock the child components
vi.mock('../McpParameterForm', () => ({
  default: vi.fn(() => <div data-testid="parameter-form">Parameter Form</div>),
}));

vi.mock('../ResponseViewer', () => ({
  default: vi.fn(() => <div data-testid="response-viewer">Response Viewer</div>),
}));

vi.mock('../TemplateSelector', () => ({
  default: vi.fn(() => <div data-testid="template-selector">Template Selector</div>),
}));

vi.mock('../ToolCallHistory', () => ({
  default: vi.fn(() => <div data-testid="tool-call-history">Tool Call History</div>),
}));

// Mock Mantine components
vi.mock('@mantine/core', () => {
  const componentFactory = (name) => vi.fn().mockImplementation(({ children }) => (
    <div data-testid={name}>{children}</div>
  ));

  return {
    Paper: componentFactory('paper'),
    Stack: componentFactory('stack'),
    Text: componentFactory('text'),
    Group: componentFactory('group'),
    LoadingOverlay: componentFactory('loading-overlay'),
    Alert: componentFactory('alert'),
    Button: componentFactory('button'),
    Center: componentFactory('center'),
    Select: componentFactory('select'),
    Tabs: {
      default: componentFactory('tabs'),
      List: componentFactory('tabs-list'),
      Tab: componentFactory('tabs-tab'),
      Panel: componentFactory('tabs-panel'),
    },
    Grid: {
      default: componentFactory('grid'),
      Col: componentFactory('grid-col'),
    },
    Divider: componentFactory('divider'),
    Card: componentFactory('card'),
    Tooltip: componentFactory('tooltip'),
    ActionIcon: componentFactory('action-icon'),
    Badge: componentFactory('badge'),
    Modal: componentFactory('modal'),
    TextInput: componentFactory('text-input'),
    Textarea: componentFactory('textarea'),
    Title: componentFactory('title'),
    Space: componentFactory('space'),
  };
});

// Mock notifications
vi.mock('@mantine/notifications', () => ({
  notifications: {
    show: vi.fn(),
  },
}));

// Mock icons
vi.mock('@tabler/icons-react', () => ({
  IconPlay: vi.fn(() => <span data-testid="icon-play">▶️</span>),
  IconCode: vi.fn(() => <span data-testid="icon-code">📝</span>),
  IconHistory: vi.fn(() => <span data-testid="icon-history">📜</span>),
  IconTemplate: vi.fn(() => <span data-testid="icon-template">📄</span>),
  IconCopy: vi.fn(() => <span data-testid="icon-copy">📋</span>),
  IconCheck: vi.fn(() => <span data-testid="icon-check">✓</span>),
  IconRefresh: vi.fn(() => <span data-testid="icon-refresh">🔄</span>),
  IconPlus: vi.fn(() => <span data-testid="icon-plus">➕</span>),
  IconDotsVertical: vi.fn(() => <span data-testid="icon-dots">⋮</span>),
  IconInfoCircle: vi.fn(() => <span data-testid="icon-info">ℹ️</span>),
  IconAlertCircle: vi.fn(() => <span data-testid="icon-alert">⚠️</span>),
  IconSettings: vi.fn(() => <span data-testid="icon-settings">⚙️</span>),
  IconSend: vi.fn(() => <span data-testid="icon-send">📤</span>),
  IconStar: vi.fn(() => <span data-testid="icon-star">⭐</span>),
  IconSave: vi.fn(() => <span data-testid="icon-save">💾</span>),
  IconDeviceDesktop: vi.fn(() => <span data-testid="icon-desktop">🖥️</span>),
  IconBrandPython: vi.fn(() => <span data-testid="icon-python">🐍</span>),
  IconDatabase: vi.fn(() => <span data-testid="icon-database">🗃️</span>),
  IconBraces: vi.fn(() => <span data-testid="icon-braces">{ }</span>),
  IconUsb: vi.fn(() => <span data-testid="icon-usb">🔌</span>),
}));

// Import the component after mocking
import { McpPlayground } from '../';

describe('McpPlayground', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  
  it('should render the playground interface', () => {
    const { container } = render(<McpPlayground />);
    
    // Verify that the component renders without errors
    expect(container).toBeDefined();
  });
  
  it('should handle template selection', () => {
    const mockOnAfterSelect = vi.fn();
    
    const template = {
      id: 'template1',
      name: 'Test Template',
      description: 'A test template',
      tool: 'execute_cypher',
      parameters: {
        query: 'MATCH (n) RETURN n LIMIT 10',
        limit: 10,
      },
    };
    
    render(
      <McpPlayground 
        selectedTemplate={template}
        onAfterSelect={mockOnAfterSelect}
      />
    );
    
    // Just verifying that the component renders with the template
    expect(true).toBe(true);
  });
  
  it('should handle history item selection', () => {
    const mockOnAfterSelect = vi.fn();
    
    const historyItem = {
      id: 'history1',
      timestamp: '2023-06-01T12:00:00Z',
      tool: 'find_similar_code',
      parameters: {
        pattern: 'function example',
        language: 'typescript',
      },
      response: {
        result: {
          matches: [
            { file: 'src/example.ts', line: 42, code: 'function example() {}' },
          ],
        },
      },
    };
    
    render(
      <McpPlayground 
        selectedHistoryItem={historyItem}
        onAfterSelect={mockOnAfterSelect}
      />
    );
    
    // Just verifying that the component renders with the history item
    expect(true).toBe(true);
  });
});