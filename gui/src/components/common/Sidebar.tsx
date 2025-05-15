import React from 'react';
import { Box, NavLink, Stack, useMantineTheme, Text, MediaQuery, Group, Badge } from '@mantine/core';
import {
  IconGraph,
  IconDatabase,
  IconSettings,
  IconCode,
  IconMessage,
  IconDashboard
} from '@tabler/icons-react';

interface SidebarProps {
  active?: string;
  onNavigate: (path: string) => void;
  collapsed?: boolean;
}

/**
 * Sidebar navigation component with responsive layout support
 */
const Sidebar: React.FC<SidebarProps> = ({
  active,
  onNavigate,
  collapsed = false
}) => {
  const theme = useMantineTheme();

  const navItems = [
    {
      label: 'Graph',
      path: '/graph',
      icon: <IconGraph size={20} />,
      description: 'View and explore code graph'
    },
    {
      label: 'Ingestion',
      path: '/ingestion',
      icon: <IconDatabase size={20} />,
      description: 'Manage code ingestion',
      badge: { label: 'Jobs', color: 'blue' }
    },
    {
      label: 'Configuration',
      path: '/config',
      icon: <IconSettings size={20} />,
      description: 'Configure system settings'
    },
    {
      label: 'MCP Playground',
      path: '/mcp',
      icon: <IconCode size={20} />,
      description: 'Experiment with MCP tools'
    },
    {
      label: 'Ask Questions',
      path: '/ask',
      icon: <IconMessage size={20} />,
      description: 'Query the graph in natural language'
    },
    {
      label: 'Dashboard',
      path: '/dashboard',
      icon: <IconDashboard size={20} />,
      description: 'View system metrics'
    },
  ];

  return (
    <Box
      sx={(theme) => ({
        width: collapsed ? 70 : 250,
        minHeight: 'calc(100vh - 60px)',
        borderRight: `1px solid ${theme.colorScheme === 'dark' ? theme.colors.dark[5] : theme.colors.gray[3]}`,
        backgroundColor: theme.colorScheme === 'dark' ? theme.colors.dark[7] : theme.white,
        padding: collapsed ? theme.spacing.xs : theme.spacing.md,
        transition: 'width 200ms ease, padding 200ms ease',
      })}
      data-testid="sidebar"
    >
      <Stack spacing={collapsed ? 0 : "xs"}>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            label={!collapsed && item.label}
            description={!collapsed && item.description}
            icon={item.icon}
            active={active === item.path}
            onClick={() => onNavigate(item.path)}
            styles={(theme) => ({
              root: {
                borderRadius: theme.radius.sm,
                margin: collapsed ? '0 0 5px 0' : undefined
              },
              icon: collapsed ? {
                margin: '0 auto',
              } : undefined,
              body: collapsed ? { display: 'none' } : undefined,
            })}
            rightSection={
              !collapsed && item.badge && (
                <Badge
                  size="sm"
                  color={item.badge.color}
                  variant="filled"
                >
                  {item.badge.label}
                </Badge>
              )
            }
            aria-label={item.label}
          />
        ))}
      </Stack>
    </Box>
  );
};

export default Sidebar;