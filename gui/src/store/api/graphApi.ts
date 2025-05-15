import { baseApi } from './baseApi';
import { GraphData } from '../../utils/graph';

/**
 * Types for Graph API
 */
export interface GraphQueryRequest {
  query: string;
  parameters?: Record<string, any>;
}

export interface GraphQueryResponse {
  records?: Array<Record<string, any>>;
  results?: Record<string, any>;
  error?: string;
}

/**
 * API endpoints for graph operations
 */
export const graphApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    executeQuery: builder.mutation<GraphQueryResponse, GraphQueryRequest>({
      query: (request) => ({
        url: '/query',
        method: 'POST',
        body: request,
      }),
    }),
    
    askQuestion: builder.mutation<{ answer: string }, { question: string }>({
      query: (request) => ({
        url: '/ask',
        method: 'POST',
        body: request,
      }),
    }),
    
    getVisualization: builder.query<string, void | { type?: string; theme?: string }>({
      query: (params) => ({
        url: '/visualize',
        params,
        responseHandler: 'text',
        headers: {
          Accept: 'text/html',
        },
      }),
    }),
  }),
});

export const {
  useExecuteQueryMutation,
  useAskQuestionMutation,
  useGetVisualizationQuery,
} = graphApi;