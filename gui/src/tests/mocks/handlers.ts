import { http, HttpResponse, delay } from 'msw';
import { API_BASE_URL } from '../../utils/api';

// Sample job data for tests
const sampleJobs = [
  {
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
  {
    job_id: '223e4567-e89b-12d3-a456-426614174001',
    repository_path: '/test/repo/path2',
    status: 'completed',
    created_at: '2023-05-28T10:00:00Z',
    started_at: '2023-05-28T10:01:00Z',
    completed_at: '2023-05-28T10:30:00Z',
    steps: [
      {
        step_id: 'step1',
        name: 'filesystem',
        status: 'completed',
        progress: 100,
        started_at: '2023-05-28T10:01:10Z',
        completed_at: '2023-05-28T10:10:00Z',
      },
      {
        step_id: 'step2',
        name: 'summarizer',
        status: 'completed',
        progress: 100,
        started_at: '2023-05-28T10:10:10Z',
        completed_at: '2023-05-28T10:20:00Z',
      },
      {
        step_id: 'step3',
        name: 'docgrapher',
        status: 'completed',
        progress: 100,
        started_at: '2023-05-28T10:20:10Z',
        completed_at: '2023-05-28T10:30:00Z',
      },
    ],
  },
];

// Define mock configuration for config tests
const mockConfig = {
  database: {
    url: 'neo4j://localhost:7687',
    username: 'neo4j',
    password: '********',
  },
  service: {
    port: 8000,
    debug: true,
    logLevel: 'info',
  },
};

const mockSchema = {
  $schema: 'http://json-schema.org/draft-07/schema#',
  type: 'object',
  required: ['database.url', 'service.port'],
  properties: {
    'database.url': {
      type: 'string',
      title: 'Database URL',
      description: 'URL for connecting to the database',
    },
    'database.username': {
      type: 'string',
      title: 'Database Username',
    },
    'database.password': {
      type: 'string',
      format: 'password',
      title: 'Database Password',
      secret: true,
    },
    'service.port': {
      type: 'integer',
      title: 'Service Port',
      minimum: 1024,
      maximum: 65535,
    },
    'service.debug': {
      type: 'boolean',
      title: 'Debug Mode',
    },
    'service.logLevel': {
      type: 'string',
      enum: ['debug', 'info', 'warning', 'error'],
      title: 'Log Level',
    },
  },
};

// Mock handlers for API requests
export const handlers = [
  // List ingestion jobs
  http.get(`${API_BASE_URL}/v1/ingest/jobs`, async () => {
    await delay(100);
    return HttpResponse.json({ jobs: sampleJobs });
  }),

  // Get ingestion status
  http.get(`${API_BASE_URL}/v1/ingest/:jobId`, async ({ params }) => {
    await delay(100);
    const jobId = params.jobId as string;
    const job = sampleJobs.find(j => j.job_id === jobId);
    if (job) {
      return HttpResponse.json(job);
    }
    return new HttpResponse(null, { status: 404 });
  }),

  // Start ingestion
  http.post(`${API_BASE_URL}/v1/ingest`, async ({ request }) => {
    await delay(100);
    const data = await request.json();
    return HttpResponse.json({
      job_id: '323e4567-e89b-12d3-a456-426614174002',
      repository_path: data.repository_path,
      status: 'pending',
    });
  }),

  // Stop ingestion
  http.post(`${API_BASE_URL}/v1/ingest/:jobId/stop`, async () => {
    await delay(100);
    return HttpResponse.json({ success: true, message: 'Job stopped successfully' });
  }),

  // Get configuration
  http.get(`${API_BASE_URL}/v1/config`, async ({ request }) => {
    await delay(50);
    const url = new URL(request.url);
    const includeSensitive = url.searchParams.get('include_sensitive') === 'true';

    // If sensitive data is requested, return actual passwords
    const config = { ...mockConfig };
    if (includeSensitive) {
      config.database.password = 'password123';
    }

    return HttpResponse.json(config);
  }),

  // Get configuration schema
  http.get(`${API_BASE_URL}/v1/config/schema`, async () => {
    await delay(50);
    return HttpResponse.json(mockSchema);
  }),

  // Update configuration
  http.patch(`${API_BASE_URL}/v1/config`, async ({ request }) => {
    await delay(50);
    const data = await request.json();
    return HttpResponse.json(data);
  }),
];