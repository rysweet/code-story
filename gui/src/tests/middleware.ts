import { AnyAction, Middleware } from '@reduxjs/toolkit';

/**
 * Creates a middleware that intercepts RTK Query hooks and injects mock implementations
 */
export function injectStoreMiddleware(): Middleware {
  return () => (next) => (action: AnyAction) => {
    // Handle any special RTK Query actions here as needed
    return next(action);
  };
}

/**
 * Mock implementations for RTK Query hooks
 */
export const mockUseStartIngestionMutation = vi.fn().mockReturnValue([
  vi.fn().mockReturnValue(Promise.resolve({ data: { job_id: 'mock-job-id' } })),
  { isLoading: false, error: null },
]);

export const mockUseListIngestionJobsQuery = vi.fn().mockReturnValue({
  data: {
    jobs: [
      {
        job_id: '123e4567-e89b-12d3-a456-426614174000',
        repository_path: '/test/repo/path',
        status: 'running',
        created_at: '2023-06-01T12:00:00Z',
        started_at: '2023-06-01T12:01:00Z',
      },
      {
        job_id: '223e4567-e89b-12d3-a456-426614174001',
        repository_path: '/test/repo/path2',
        status: 'completed',
        created_at: '2023-05-28T10:00:00Z',
        started_at: '2023-05-28T10:01:00Z',
        completed_at: '2023-05-28T10:30:00Z',
      },
    ],
  },
  isLoading: false,
  error: null,
  refetch: vi.fn(),
});

export const mockUseGetIngestionStatusQuery = vi.fn().mockReturnValue({
  data: {
    job_id: '123e4567-e89b-12d3-a456-426614174000',
    repository_path: '/test/repo/path',
    status: 'running',
    created_at: '2023-06-01T12:00:00Z',
    started_at: '2023-06-01T12:01:00Z',
    steps: [
      {
        step_id: 'step1',
        name: 'filesystem',
        status: 'completed',
        progress: 100,
        started_at: '2023-06-01T12:01:10Z',
        completed_at: '2023-06-01T12:02:00Z',
      },
      {
        step_id: 'step2',
        name: 'summarizer',
        status: 'running',
        progress: 50,
        started_at: '2023-06-01T12:02:10Z',
      },
    ],
  },
  isLoading: false,
  error: null,
  refetch: vi.fn(),
});

export const mockUseStopIngestionMutation = vi.fn().mockReturnValue([
  vi.fn().mockReturnValue(Promise.resolve({ data: { success: true } })),
  { isLoading: false, error: null },
]);