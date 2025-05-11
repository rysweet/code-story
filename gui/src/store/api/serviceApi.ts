import { baseApi } from './baseApi';

/**
 * Types for Service API
 */
export interface ServiceStatus {
  status: 'running' | 'stopped' | 'starting' | 'stopping' | 'error';
  version?: string;
  uptime?: number;
  message?: string;
  components?: {
    neo4j?: { status: string; message?: string };
    redis?: { status: string; message?: string };
    celery?: { status: string; message?: string };
    mcp?: { status: string; message?: string };
  };
}

export interface ServiceActionResponse {
  success: boolean;
  message?: string;
}

/**
 * API endpoints for service operations
 */
export const serviceApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getServiceStatus: builder.query<ServiceStatus, void>({
      query: () => '/service/status',
      providesTags: ['ServiceStatus'],
    }),
    
    startService: builder.mutation<ServiceActionResponse, void>({
      query: () => ({
        url: '/service/start',
        method: 'POST',
      }),
      invalidatesTags: ['ServiceStatus'],
    }),
    
    stopService: builder.mutation<ServiceActionResponse, void>({
      query: () => ({
        url: '/service/stop',
        method: 'POST',
      }),
      invalidatesTags: ['ServiceStatus'],
    }),
    
    getHealthCheck: builder.query<{ status: string }, void>({
      query: () => '/health',
    }),
  }),
});

export const {
  useGetServiceStatusQuery,
  useStartServiceMutation,
  useStopServiceMutation,
  useGetHealthCheckQuery,
} = serviceApi;