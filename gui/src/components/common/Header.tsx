import React from 'react';
import { Box, Group, Title, Button, ActionIcon, useMantineColorScheme } from '@mantine/core';
import { IconSun, IconMoon, IconServer } from '@tabler/icons-react';

interface HeaderProps {
  toggleServicePanel?: () => void;
  isMobile?: boolean;
}

/**
 * Header component for the application
 * Displays the application title, theme toggle, and service status button
 */
const Header: React.FC<HeaderProps> = ({ toggleServicePanel, isMobile }) => {
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const dark = colorScheme === 'dark';

  return (
    <Box
      py="md"
      px={isMobile ? "xs" : "lg"}
      sx={(theme) => ({
        borderBottom: `1px solid ${theme.colors.gray[3]}`,
        backgroundColor: theme.colorScheme === 'dark' ? theme.colors.dark[7] : theme.white,
        width: '100%'
      })}
    >
      <Group justify="space-between" noWrap>
        <Title order={isMobile ? 4 : 3} style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>Code Story</Title>
        <Group spacing={isMobile ? "xs" : "md"} noWrap>
          <ActionIcon
            variant="default"
            onClick={() => toggleColorScheme()}
            size={isMobile ? 24 : 30}
            title={dark ? 'Light mode' : 'Dark mode'}
            aria-label="Toggle color scheme"
          >
            {dark ? <IconSun size={isMobile ? 14 : 16} /> : <IconMoon size={isMobile ? 14 : 16} />}
          </ActionIcon>
          {isMobile ? (
            <ActionIcon
              size={24}
              variant="light"
              color="blue"
              onClick={toggleServicePanel}
              title="Service Status"
            >
              <IconServer size={14} />
            </ActionIcon>
          ) : (
            <Button
              variant="light"
              leftIcon={<IconServer size={16} />}
              onClick={toggleServicePanel}
              size="sm"
            >
              Service Status
            </Button>
          )}
        </Group>
      </Group>
    </Box>
  );
};

export default Header;