import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { MantineProvider } from '@mantine/core';

// Mock Mantine components
vi.mock('@mantine/core', () => ({
  Box: ({ children, py, px }: any) => (
    <div data-testid="header-box" data-px={px} data-py={py}>{children}</div>
  ),
  Group: ({ children, justify, noWrap, spacing }: any) => (
    <div data-testid="header-group" data-justify={justify} data-spacing={spacing} data-nowrap={noWrap?.toString()}>{children}</div>
  ),
  Title: ({ children, order, style }: any) => (
    <h3 data-testid="app-title" data-order={order}>{children}</h3>
  ),
  Button: ({ children, variant, leftIcon, onClick, size }: any) => (
    <button
      data-testid="service-status-button"
      data-variant={variant}
      data-size={size}
      onClick={onClick}
    >
      {leftIcon && <span data-testid="service-icon"></span>}
      {children}
    </button>
  ),
  ActionIcon: ({ children, variant, onClick, size, title, 'aria-label': ariaLabel }: any) => (
    <button
      data-testid="action-icon"
      data-variant={variant}
      data-size={size}
      data-title={title}
      aria-label={ariaLabel}
      onClick={onClick}
    >
      {children}
    </button>
  ),
  useMantineColorScheme: () => ({
    colorScheme: 'light',
    toggleColorScheme: vi.fn()
  }),
  MantineProvider: ({ children }: any) => <div>{children}</div>
}));

// Mock Tabler icons
vi.mock('@tabler/icons-react', () => ({
  IconSun: () => <span data-testid="sun-icon"></span>,
  IconMoon: () => <span data-testid="moon-icon"></span>,
  IconServer: () => <span data-testid="server-icon"></span>,
}));

// Import after mocking
import Header from '../Header';

describe('Header', () => {
  it('should render the application title', () => {
    render(
      <MantineProvider>
        <Header />
      </MantineProvider>
    );
    expect(screen.getByTestId('app-title')).toHaveTextContent('Code Story');
  });

  it('should render the theme toggle button', () => {
    render(
      <MantineProvider>
        <Header />
      </MantineProvider>
    );
    expect(screen.getByLabelText('Toggle color scheme')).toBeInTheDocument();
  });

  it('should render the service status button for desktop view', () => {
    render(
      <MantineProvider>
        <Header toggleServicePanel={() => {}} isMobile={false} />
      </MantineProvider>
    );
    expect(screen.getByTestId('service-status-button')).toHaveTextContent('Service Status');
  });

  it('should render the service status icon for mobile view', () => {
    render(
      <MantineProvider>
        <Header toggleServicePanel={() => {}} isMobile={true} />
      </MantineProvider>
    );
    // Find the action icon that has the Service Status title
    const actionIcons = screen.getAllByTestId('action-icon');
    const serviceIcon = actionIcons.find(icon => icon.getAttribute('data-title') === 'Service Status');
    expect(serviceIcon).toBeInTheDocument();
    expect(serviceIcon).toHaveAttribute('data-title', 'Service Status');
  });

  it('should call toggleServicePanel when service status is clicked in desktop view', async () => {
    const toggleServicePanel = vi.fn();
    const user = userEvent.setup();

    render(
      <MantineProvider>
        <Header toggleServicePanel={toggleServicePanel} isMobile={false} />
      </MantineProvider>
    );

    const button = screen.getByTestId('service-status-button');
    await user.click(button);

    expect(toggleServicePanel).toHaveBeenCalled();
  });

  it('should call toggleServicePanel when service status is clicked in mobile view', async () => {
    const toggleServicePanel = vi.fn();
    const user = userEvent.setup();

    render(
      <MantineProvider>
        <Header toggleServicePanel={toggleServicePanel} isMobile={true} />
      </MantineProvider>
    );

    // Find the action icon that has the Service Status data-title attribute
    const actionIcons = screen.getAllByTestId('action-icon');
    const serviceIcon = actionIcons.find(icon => icon.getAttribute('data-title') === 'Service Status');
    expect(serviceIcon).toBeInTheDocument();

    if (serviceIcon) {
      await user.click(serviceIcon);
    }

    expect(toggleServicePanel).toHaveBeenCalled();
  });
});