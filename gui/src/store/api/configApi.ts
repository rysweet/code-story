import { baseApi } from './baseApi';

/**
 * Database clear request interface
 */
interface DatabaseClearRequest {
  confirm: boolean;
  preserve_schema: boolean;
}

/**
 * Database clear response interface
 */
interface DatabaseClearResponse {
  status: string;
  message: string;
  timestamp: string;
}

/**
 * API endpoints for configuration operations
 */
export const configApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getConfig: builder.query<Record<string, any>, boolean | void>({
      query: (includeSensitive = false) => ({
        url: '/config',
        params: includeSensitive ? { include_sensitive: 'true' } : undefined,
      }),
      providesTags: ['Config'],
    }),
    
    getConfigSchema: builder.query<Record<string, any>, void>({
      query: () => '/config/schema',
    }),
    
    updateConfig: builder.mutation<Record<string, any>, Record<string, any>>({
      query: (configUpdates) => ({
        url: '/config',
        method: 'PATCH',
        body: configUpdates,
      }),
      invalidatesTags: ['Config'],
    }),
    
    clearDatabase: builder.mutation<DatabaseClearResponse, DatabaseClearRequest>({
      query: (request) => ({
        url: '/database/clear',
        method: 'POST',
        body: request,
      }),
    }),
  }),
});

export const {
  useGetConfigQuery,
  useGetConfigSchemaQuery,
  useUpdateConfigMutation,
  useClearDatabaseMutation,
} = configApi;