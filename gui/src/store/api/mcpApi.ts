import { baseApi } from './baseApi';

/**
 * Types for MCP API
 */
export interface ToolCall {
  tool: string;
  parameters: Record<string, any>;
}

export interface ToolResponse {
  result: any;
  error?: string;
}

export interface ToolCallHistoryItem {
  id: string;
  timestamp: string;
  tool: string;
  parameters: Record<string, any>;
  response: ToolResponse;
}

export interface SavedToolCallTemplate {
  id: string;
  name: string;
  description?: string;
  tool: string;
  parameters: Record<string, any>;
}

export interface McpAvailableTools {
  tools: {
    name: string;
    description: string;
    parameters: Record<string, any>;
  }[];
}

/**
 * API endpoints for MCP operations
 */
export const mcpApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    // Execute tool call
    executeTool: builder.mutation<ToolResponse, ToolCall>({
      query: (request) => ({
        url: '/mcp/tool',
        method: 'POST',
        body: request,
      }),
    }),
    
    // Get available tools
    getAvailableTools: builder.query<McpAvailableTools, void>({
      query: () => '/mcp/tools',
    }),
    
    // Get tool call history
    getToolCallHistory: builder.query<ToolCallHistoryItem[], void>({
      query: () => '/mcp/history',
    }),
    
    // Save tool call template
    saveToolCallTemplate: builder.mutation<SavedToolCallTemplate, SavedToolCallTemplate>({
      query: (template) => ({
        url: '/mcp/templates',
        method: 'POST',
        body: template,
      }),
      invalidatesTags: ['McpTemplates'],
    }),
    
    // Get saved tool call templates
    getSavedTemplates: builder.query<SavedToolCallTemplate[], void>({
      query: () => '/mcp/templates',
      providesTags: ['McpTemplates'],
    }),
    
    // Delete saved tool call template
    deleteTemplate: builder.mutation<{ success: boolean }, string>({
      query: (templateId) => ({
        url: `/mcp/templates/${templateId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['McpTemplates'],
    }),
  }),
  overrideExisting: false,
});

export const {
  useExecuteToolMutation,
  useGetAvailableToolsQuery,
  useGetToolCallHistoryQuery,
  useSaveToolCallTemplateMutation,
  useGetSavedTemplatesQuery,
  useDeleteTemplateMutation,
} = mcpApi;