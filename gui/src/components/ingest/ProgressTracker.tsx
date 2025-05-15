import React, { useEffect, useState } from 'react';
import {
  Card,
  Progress,
  Text,
  Group,
  ActionIcon,
  Stack,
  Badge,
  Button,
  Alert,
  Timeline,
  Center,
  Loader
} from '@mantine/core';
import { 
  IconX, 
  IconRefresh, 
  IconCheck, 
  IconClock, 
  IconAlertTriangle,
  IconRocket,
  IconAdjustments
} from '@tabler/icons-react';
import { useGetIngestionStatusQuery, useStopIngestionMutation, IngestionJob, IngestionStep } from '../../store';
import useWebSocket from '../../hooks/useWebSocket';
import { formatDate, formatDuration } from '../../utils/formatters';

interface ProgressTrackerProps {
  jobId: string;
  onClose?: () => void;
}

/**
 * Component for tracking ingestion job progress
 */
const ProgressTracker: React.FC<ProgressTrackerProps> = ({ jobId, onClose }) => {
  const { data: jobStatus, isLoading, error, refetch } = useGetIngestionStatusQuery(jobId);
  const [stopJob, { isLoading: isStopping }] = useStopIngestionMutation();
  
  // Connect to WebSocket for real-time updates
  const { 
    isConnected: isWsConnected, 
    message: wsUpdate 
  } = useWebSocket<any>(`/status/${jobId}`, null);
  
  // Calculate overall progress based on steps
  const calculateOverallProgress = (job: IngestionJob): number => {
    if (!job.steps || job.steps.length === 0) return 0;
    
    // Sum up progress from all steps and divide by number of steps
    const totalProgress = job.steps.reduce(
      (sum, step) => sum + (step.progress || 0), 
      0
    );
    
    return Math.floor(totalProgress / job.steps.length);
  };
  
  // Get the status badge color based on status
  const getStatusColor = (status: string): string => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'green';
      case 'running':
        return 'blue';
      case 'pending':
        return 'yellow';
      case 'failed':
        return 'red';
      case 'cancelled':
      case 'skipped':
        return 'gray';
      default:
        return 'gray';
    }
  };
  
  // Get the status icon based on status
  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <IconCheck size={16} />;
      case 'running':
        return <Loader size={16} />;
      case 'pending':
        return <IconClock size={16} />;
      case 'failed':
        return <IconX size={16} />;
      case 'cancelled':
      case 'skipped':
        return <IconAlertTriangle size={16} />;
      default:
        return null;
    }
  };
  
  // Handle stopping the job
  const handleStopJob = async () => {
    try {
      await stopJob(jobId).unwrap();
      refetch();
    } catch (err) {
      console.error('Failed to stop job:', err);
    }
  };
  
  // Get currently active step
  const getActiveStep = (job: IngestionJob): IngestionStep | null => {
    if (!job.steps || job.steps.length === 0) return null;
    
    return job.steps.find(step => step.status === 'running') || null;
  };
  
  // Calculate job duration
  const getJobDuration = (job: IngestionJob): string => {
    if (!job.started_at) return 'Not started';
    
    const startTime = new Date(job.started_at).getTime();
    const endTime = job.completed_at 
      ? new Date(job.completed_at).getTime() 
      : new Date().getTime();
    
    const durationSeconds = (endTime - startTime) / 1000;
    return formatDuration(durationSeconds);
  };
  
  if (isLoading) {
    return (
      <Card shadow="sm" radius="md" p="md" withBorder>
        <Center py="xl">
          <Loader />
          <Text ml="md">Loading job status...</Text>
        </Center>
      </Card>
    );
  }
  
  if (error || !jobStatus) {
    return (
      <Card shadow="sm" radius="md" p="md" withBorder>
        <Alert color="red" title="Error" icon={<IconX size={16} />}>
          Failed to load job status. Please try again.
        </Alert>
        <Group position="right" mt="md">
          <Button onClick={() => refetch()} leftIcon={<IconRefresh size={16} />}>
            Retry
          </Button>
          {onClose && (
            <Button onClick={onClose} variant="subtle">
              Close
            </Button>
          )}
        </Group>
      </Card>
    );
  }
  
  const activeStep = getActiveStep(jobStatus);
  const overallProgress = calculateOverallProgress(jobStatus);
  
  return (
    <Card shadow="sm" radius="md" p="md" withBorder>
      <Stack spacing="md">
        <Group position="apart">
          <Text weight={500} size="lg">Ingestion Progress</Text>
          <Group spacing="xs">
            <ActionIcon onClick={() => refetch()} title="Refresh">
              <IconRefresh size={16} />
            </ActionIcon>
            {onClose && (
              <ActionIcon onClick={onClose} title="Close">
                <IconX size={16} />
              </ActionIcon>
            )}
          </Group>
        </Group>
        
        <Group position="apart">
          <Text>Job ID: <Text span tt="monospace">{jobId}</Text></Text>
          <Badge 
            color={getStatusColor(jobStatus.status)}
            variant="filled"
            leftSection={getStatusIcon(jobStatus.status)}
          >
            {jobStatus.status}
          </Badge>
        </Group>
        
        <Group position="apart">
          <Text>Repository: {jobStatus.repository_path}</Text>
        </Group>
        
        <Group position="apart">
          <Text>Started: {jobStatus.started_at ? formatDate(jobStatus.started_at) : 'Not started'}</Text>
          <Text>Duration: {getJobDuration(jobStatus)}</Text>
        </Group>
        
        <Stack spacing="xs">
          <Text weight={500} size="sm">Overall Progress: {overallProgress}%</Text>
          <Progress 
            value={overallProgress} 
            size="xl" 
            radius="xl" 
            color={jobStatus.status === 'failed' ? 'red' : undefined}
            striped={jobStatus.status === 'running'}
            animate={jobStatus.status === 'running'}
          />
        </Stack>
        
        {activeStep && (
          <Alert color="blue" title={`Currently running: ${activeStep.name}`} icon={<IconRocket size={16} />}>
            <Text size="sm">Progress: {activeStep.progress}%</Text>
            {activeStep.message && <Text size="sm">{activeStep.message}</Text>}
          </Alert>
        )}
        
        <Timeline active={jobStatus.steps?.findIndex(s => s.status === 'running')} bulletSize={24} lineWidth={2}>
          {jobStatus.steps?.map((step) => (
            <Timeline.Item 
              key={step.step_id} 
              title={step.name} 
              bullet={getStatusIcon(step.status)} 
              color={getStatusColor(step.status)}
            >
              <Text color="dimmed" size="sm">Status: {step.status}</Text>
              <Text color="dimmed" size="sm">Progress: {step.progress}%</Text>
              {step.message && <Text color="dimmed" size="sm">{step.message}</Text>}
              {step.started_at && (
                <Text color="dimmed" size="sm">
                  Started: {formatDate(step.started_at)}
                </Text>
              )}
              {step.completed_at && (
                <Text color="dimmed" size="sm">
                  Completed: {formatDate(step.completed_at)}
                </Text>
              )}
            </Timeline.Item>
          ))}
        </Timeline>
        
        {jobStatus.error && (
          <Alert color="red" title="Error" icon={<IconX size={16} />}>
            {jobStatus.error}
          </Alert>
        )}
        
        <Group position="right">
          {['running', 'pending'].includes(jobStatus.status) && (
            <Button 
              color="red" 
              onClick={handleStopJob} 
              loading={isStopping}
              leftIcon={<IconX size={16} />}
            >
              Stop Ingestion
            </Button>
          )}
          
          {onClose && (
            <Button onClick={onClose} variant="subtle">
              Close
            </Button>
          )}
        </Group>
      </Stack>
    </Card>
  );
};

export default ProgressTracker;