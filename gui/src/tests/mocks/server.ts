import { setupServer } from 'msw/node';
import { beforeAll, afterAll, afterEach } from 'vitest';
import { handlers } from './handlers';

// Setup MSW server for API mocking in tests
export const server = setupServer(...handlers);

// Define global setup/teardown for tests
export function setupMswTestServer() {
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
}