import { baseApi } from './baseApi';

/**
 * Types for Ingestion API
 */
export interface IngestionRequest {
  repository_path: string;
  options?: Record<string, any>;
}

export interface IngestionJob {
  job_id: string;
  repository_path: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  steps?: IngestionStep[];
}

export interface IngestionStep {
  step_id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  progress: number;
  message?: string;
  started_at?: string;
  completed_at?: string;
}

export interface IngestionResponse {
  job_id: string;
  repository_path: string;
  status: string;
}

export interface JobListResponse {
  jobs: IngestionJob[];
}

/**
 * API endpoints for ingestion operations
 */
export const ingestApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    startIngestion: builder.mutation<IngestionResponse, IngestionRequest>({
      query: (request) => ({
        url: '/ingest',
        method: 'POST',
        body: request,
      }),
      invalidatesTags: ['IngestionJobs'],
    }),
    
    getIngestionStatus: builder.query<IngestionJob, string>({
      query: (jobId) => `/ingest/${jobId}`,
      providesTags: (result, error, jobId) => 
        result ? [{ type: 'IngestStatus', id: jobId }] : ['IngestStatus'],
    }),
    
    stopIngestion: builder.mutation<{ success: boolean; message?: string }, string>({
      query: (jobId) => ({
        url: `/ingest/${jobId}/stop`,
        method: 'POST',
      }),
      invalidatesTags: (result, error, jobId) => [
        { type: 'IngestStatus', id: jobId },
        'IngestionJobs',
      ],
    }),
    
    listIngestionJobs: builder.query<JobListResponse, void>({
      query: () => '/ingest/jobs',
      providesTags: ['IngestionJobs'],
    }),
  }),
});

export const {
  useStartIngestionMutation,
  useGetIngestionStatusQuery,
  useStopIngestionMutation,
  useListIngestionJobsQuery,
} = ingestApi;