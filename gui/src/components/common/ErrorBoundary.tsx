import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Alert, Button, Stack, Text } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary component to catch and display errors
 */
class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Alert
          icon={<IconAlertCircle size={16} />}
          title="Something went wrong"
          color="red"
          variant="filled"
        >
          <Stack spacing="md">
            <Text>An error occurred while rendering this component.</Text>
            <Text size="sm" color="dimmed">
              {this.state.error?.message || 'Unknown error'}
            </Text>
            <Button
              variant="white"
              color="red"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Try again
            </Button>
          </Stack>
        </Alert>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;