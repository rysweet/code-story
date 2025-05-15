import { describe, it, expect, vi } from 'vitest';
import { mcpApi } from '../mcpApi';

describe('mcpApi', () => {
  it('should define endpoint for executeTool', () => {
    const endpoints = mcpApi.endpoints;
    expect(endpoints.executeTool).toBeDefined();
    expect(endpoints.executeTool.name).toBe('executeTool');
  });
  
  it('should define endpoint for getAvailableTools', () => {
    const endpoints = mcpApi.endpoints;
    expect(endpoints.getAvailableTools).toBeDefined();
    expect(endpoints.getAvailableTools.name).toBe('getAvailableTools');
  });
  
  it('should define endpoint for getToolCallHistory', () => {
    const endpoints = mcpApi.endpoints;
    expect(endpoints.getToolCallHistory).toBeDefined();
    expect(endpoints.getToolCallHistory.name).toBe('getToolCallHistory');
  });
  
  it('should define endpoint for saveToolCallTemplate', () => {
    const endpoints = mcpApi.endpoints;
    expect(endpoints.saveToolCallTemplate).toBeDefined();
    expect(endpoints.saveToolCallTemplate.name).toBe('saveToolCallTemplate');
  });
  
  it('should define endpoint for getSavedTemplates', () => {
    const endpoints = mcpApi.endpoints;
    expect(endpoints.getSavedTemplates).toBeDefined();
    expect(endpoints.getSavedTemplates.name).toBe('getSavedTemplates');
  });
  
  it('should define endpoint for deleteTemplate', () => {
    const endpoints = mcpApi.endpoints;
    expect(endpoints.deleteTemplate).toBeDefined();
    expect(endpoints.deleteTemplate.name).toBe('deleteTemplate');
  });
  
  it('should export hooks for all endpoints', () => {
    expect(mcpApi.useExecuteToolMutation).toBeDefined();
    expect(mcpApi.useGetAvailableToolsQuery).toBeDefined();
    expect(mcpApi.useGetToolCallHistoryQuery).toBeDefined();
    expect(mcpApi.useSaveToolCallTemplateMutation).toBeDefined();
    expect(mcpApi.useGetSavedTemplatesQuery).toBeDefined();
    expect(mcpApi.useDeleteTemplateMutation).toBeDefined();
  });
});