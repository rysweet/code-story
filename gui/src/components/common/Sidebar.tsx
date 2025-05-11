import React from 'react';
import { Box, NavLink, Stack } from '@mantine/core';
import { 
  IconGraph, 
  IconDatabase, 
  IconSettings, 
  IconCode, 
  IconMessage 
} from '@tabler/icons-react';

/**
 * Sidebar navigation component
 */
const Sidebar: React.FC<{ active?: string; onNavigate: (path: string) => void }> = ({ 
  active, 
  onNavigate 
}) => {
  const navItems = [
    { label: 'Graph', path: '/graph', icon: <IconGraph size={20} /> },
    { label: 'Ingestion', path: '/ingestion', icon: <IconDatabase size={20} /> },
    { label: 'Configuration', path: '/config', icon: <IconSettings size={20} /> },
    { label: 'MCP Playground', path: '/mcp', icon: <IconCode size={20} /> },
    { label: 'Ask Questions', path: '/ask', icon: <IconMessage size={20} /> },
  ];

  return (
    <Box
      sx={(theme) => ({
        width: 250,
        minHeight: 'calc(100vh - 60px)',
        borderRight: `1px solid ${theme.colors.gray[3]}`,
        backgroundColor: theme.white,
        padding: theme.spacing.md,
      })}
    >
      <Stack spacing="xs">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            label={item.label}
            icon={item.icon}
            active={active === item.path}
            onClick={() => onNavigate(item.path)}
          />
        ))}
      </Stack>
    </Box>
  );
};

export default Sidebar;