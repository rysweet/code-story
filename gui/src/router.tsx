import React from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';

import Layout from './components/common/Layout';
import GraphPage from './pages/GraphPage';
import IngestionPage from './pages/IngestionPage';
import ConfigPage from './pages/ConfigPage';
import McpPage from './pages/McpPage';
import AskPage from './pages/AskPage';
import ErrorBoundary from './components/common/ErrorBoundary';

/**
 * Application routes
 */
const routes = [
  {
    path: '/',
    element: <Layout />,
    errorElement: <ErrorBoundary />,
    children: [
      {
        index: true,
        element: <GraphPage />,
      },
      {
        path: 'graph',
        element: <GraphPage />,
      },
      {
        path: 'ingestion',
        element: <IngestionPage />,
      },
      {
        path: 'config',
        element: <ConfigPage />,
      },
      {
        path: 'mcp',
        element: <McpPage />,
      },
      {
        path: 'ask',
        element: <AskPage />,
      },
    ],
  },
];

const router = createBrowserRouter(routes);

/**
 * Router component for the application
 */
export const Router: React.FC = () => {
  return <RouterProvider router={router} />;
};

export default Router;