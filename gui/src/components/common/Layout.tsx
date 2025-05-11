import React, { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  AppShell,
  Box,
  useMantineTheme,
  useMantineColorScheme,
  ColorSchemeProvider,
  MantineProvider,
  Drawer,
  Text,
  Group,
  Title,
  Button,
  Stack,
  Badge,
  Code,
  Divider,
  ActionIcon,
  MediaQuery,
  Burger
} from '@mantine/core';
import { useDisclosure, useMediaQuery } from '@mantine/hooks';
import {
  IconServer,
  IconCheck,
  IconX,
  IconAlertTriangle,
  IconChevronLeft
} from '@tabler/icons-react';
import Header from './Header';
import Sidebar from './Sidebar';
import ErrorBoundary from './ErrorBoundary';

/**
 * Main layout component with header and sidebar
 * Includes responsive design and theme management
 */
const Layout: React.FC = () => {
  const theme = useMantineTheme();
  const [colorScheme, setColorScheme] = useState<'light' | 'dark'>(
    localStorage.getItem('colorScheme') === 'dark' ? 'dark' : 'light'
  );

  const location = useLocation();
  const navigate = useNavigate();
  const [opened, { toggle, close }] = useDisclosure(false);
  const [servicePanelOpen, setServicePanelOpen] = useState(false);
  const isMobile = useMediaQuery(`(max-width: ${theme.breakpoints.sm})`);

  // Get the current path without leading slash
  const currentPath = location.pathname === '/'
    ? 'graph'
    : location.pathname.substring(1);

  const handleNavigate = (path: string) => {
    navigate(path);
    // Close mobile sidebar when navigating
    if (isMobile) {
      close();
    }
  };

  const toggleColorScheme = (value?: 'light' | 'dark') => {
    const newColorScheme = value || (colorScheme === 'dark' ? 'light' : 'dark');
    setColorScheme(newColorScheme);
    localStorage.setItem('colorScheme', newColorScheme);
  };

  const toggleServicePanel = () => {
    setServicePanelOpen(!servicePanelOpen);
  };

  // Mock service status for demonstration
  const serviceStatus = {
    api: { status: 'running', uptime: '3d 2h 15m' },
    database: { status: 'running', uptime: '14d 7h 32m' },
    celery: { status: 'warning', message: 'High task queue' },
    llm: { status: 'running', uptime: '2d 19h 45m' },
  };

  return (
    <ColorSchemeProvider colorScheme={colorScheme} toggleColorScheme={toggleColorScheme}>
      <MantineProvider
        theme={{ colorScheme }}
        withNormalizeCSS
        withGlobalStyles
      >
        <AppShell
          padding={0}
          header={{ height: 60 }}
          navbar={{
            width: isMobile ? 0 : 250,
            breakpoint: 'sm',
            collapsed: { mobile: !opened }
          }}
          styles={(theme) => ({
            main: {
              backgroundColor: theme.colorScheme === 'dark' ? theme.colors.dark[8] : theme.colors.gray[0],
            },
            root: {
              overflow: 'hidden',
              height: '100vh',
            }
          })}
        >
          <AppShell.Header>
            <Group spacing="xs" style={{ height: '100%' }} px="md">
              <MediaQuery largerThan="sm" styles={{ display: 'none' }}>
                <Burger
                  opened={opened}
                  onClick={toggle}
                  size="sm"
                  color={theme.colors.gray[6]}
                  mr="xl"
                  aria-label="Toggle navigation"
                />
              </MediaQuery>
              <Header toggleServicePanel={toggleServicePanel} isMobile={isMobile} />
            </Group>
          </AppShell.Header>

          <AppShell.Navbar sx={{ overflow: 'hidden' }}>
            <Sidebar
              active={`/${currentPath}`}
              onNavigate={handleNavigate}
              collapsed={isMobile ? true : false}
            />
          </AppShell.Navbar>

          <AppShell.Main>
            <ErrorBoundary>
              <Box p={isMobile ? "xs" : "md"}>
                <Outlet />
              </Box>
            </ErrorBoundary>
          </AppShell.Main>
        </AppShell>

        {/* Service Status Drawer */}
        <Drawer
          opened={servicePanelOpen}
          onClose={() => setServicePanelOpen(false)}
          title={
            <Group>
              <IconServer size={20} />
              <Title order={4}>Service Status</Title>
            </Group>
          }
          padding={isMobile ? "md" : "lg"}
          position="right"
          size={isMobile ? "100%" : "md"}
        >
          <Stack spacing={isMobile ? "sm" : "md"}>
            <Text color="dimmed" size={isMobile ? "xs" : "sm"}>System services status and health information</Text>

            <Box>
              <Title order={5} mb="xs" size={isMobile ? "sm" : "md"}>API Service</Title>
              <Group spacing={isMobile ? "xs" : "md"}>
                <Badge color={serviceStatus.api.status === 'running' ? 'green' : 'red'} size={isMobile ? "xs" : "sm"}>
                  {serviceStatus.api.status}
                </Badge>
                <Text size={isMobile ? "xs" : "sm"}>Uptime: {serviceStatus.api.uptime}</Text>
              </Group>
              <Text size="xs" color="dimmed">Version: 1.0.2</Text>
            </Box>

            <Divider />

            <Box>
              <Title order={5} mb="xs" size={isMobile ? "sm" : "md"}>Database</Title>
              <Group spacing={isMobile ? "xs" : "md"}>
                <Badge color={serviceStatus.database.status === 'running' ? 'green' : 'red'} size={isMobile ? "xs" : "sm"}>
                  {serviceStatus.database.status}
                </Badge>
                <Text size={isMobile ? "xs" : "sm"}>Uptime: {serviceStatus.database.uptime}</Text>
              </Group>
              <Text size="xs" color="dimmed">Neo4j 5.18.0</Text>
            </Box>

            <Divider />

            <Box>
              <Title order={5} mb="xs" size={isMobile ? "sm" : "md"}>Task Queue (Celery)</Title>
              <Group spacing={isMobile ? "xs" : "md"}>
                <Badge color={serviceStatus.celery.status === 'warning' ? 'yellow' : 'green'} size={isMobile ? "xs" : "sm"}>
                  {serviceStatus.celery.status}
                </Badge>
                <Text size={isMobile ? "xs" : "sm"}>{serviceStatus.celery.message}</Text>
              </Group>
              <Text size="xs" color="dimmed">Active Workers: 3</Text>
            </Box>

            <Divider />

            <Box>
              <Title order={5} mb="xs" size={isMobile ? "sm" : "md"}>LLM Service</Title>
              <Group spacing={isMobile ? "xs" : "md"}>
                <Badge color={serviceStatus.llm.status === 'running' ? 'green' : 'red'} size={isMobile ? "xs" : "sm"}>
                  {serviceStatus.llm.status}
                </Badge>
                <Text size={isMobile ? "xs" : "sm"}>Uptime: {serviceStatus.llm.uptime}</Text>
              </Group>
              <Text size="xs" color="dimmed">Model: gpt-4-vision-preview</Text>
            </Box>

            <Divider />

            <Group mt={isMobile ? "sm" : "md"} position="right">
              <Button
                variant="light"
                onClick={() => setServicePanelOpen(false)}
                leftIcon={<IconChevronLeft size={isMobile ? 14 : 16} />}
                size={isMobile ? "xs" : "sm"}
              >
                Close Panel
              </Button>
            </Group>
          </Stack>
        </Drawer>
      </MantineProvider>
    </ColorSchemeProvider>
  );
};

export default Layout;