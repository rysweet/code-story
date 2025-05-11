import React from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AppShell, Box } from '@mantine/core';
import Header from './Header';
import Sidebar from './Sidebar';
import ErrorBoundary from './ErrorBoundary';

/**
 * Main layout component with header and sidebar
 */
const Layout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // Get the current path without leading slash
  const currentPath = location.pathname === '/'
    ? 'graph'
    : location.pathname.substring(1);

  const handleNavigate = (path: string) => {
    navigate(path);
  };

  return (
    <AppShell
      padding={0}
      header={{ height: 60 }}
      navbar={{ width: 250, breakpoint: 'sm' }}
    >
      <AppShell.Header>
        <Header />
      </AppShell.Header>

      <AppShell.Navbar>
        <Sidebar active={`/${currentPath}`} onNavigate={handleNavigate} />
      </AppShell.Navbar>

      <AppShell.Main>
        <ErrorBoundary>
          <Box p="md">
            <Outlet />
          </Box>
        </ErrorBoundary>
      </AppShell.Main>
    </AppShell>
  );
};

export default Layout;