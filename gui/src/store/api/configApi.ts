import { baseApi } from './baseApi';

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
  }),
});

export const {
  useGetConfigQuery,
  useGetConfigSchemaQuery,
  useUpdateConfigMutation,
} = configApi;