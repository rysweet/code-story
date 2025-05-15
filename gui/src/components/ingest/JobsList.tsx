import React from 'react';
import { 
  Card, 
  Table, 
  Badge, 
  Text, 
  Group, 
  Button, 
  Stack, 
  ActionIcon,
  Pagination,
  Menu,
  Loader,
  Alert
} from '@mantine/core';
import { 
  IconCheck, 
  IconX, 
  IconAlertTriangle, 
  IconClock, 
  IconRefresh,
  IconDotsVertical,
  IconEye,
  IconStop,
  IconTrash
} from '@tabler/icons-react';
import { useListIngestionJobsQuery, useStopIngestionMutation, IngestionJob } from '../../store';
import { formatDate, formatDuration } from '../../utils/formatters';

interface JobsListProps {
  onViewDetails?: (jobId: string) => void;
  onRefresh?: () => void;
}

/**
 * Component for displaying a list of ingestion jobs
 */
const JobsList: React.FC<JobsListProps> = ({ onViewDetails, onRefresh }) => {
  const { data, isLoading, error, refetch } = useListIngestionJobsQuery();
  const [stopJob, { isLoading: isStopping }] = useStopIngestionMutation();
  
  const [page, setPage] = React.useState(1);
  const itemsPerPage = 10;
  
  // Get the status badge color based on job status
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
        return 'gray';
      default:
        return 'gray';
    }
  };
  
  // Get the status icon based on job status
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
        return <IconAlertTriangle size={16} />;
      default:
        return null;
    }
  };
  
  // Calculate duration of job
  const getJobDuration = (job: IngestionJob): string => {
    if (!job.started_at) return 'Not started';
    
    const startTime = new Date(job.started_at).getTime();
    const endTime = job.completed_at 
      ? new Date(job.completed_at).getTime() 
      : new Date().getTime();
    
    const durationSeconds = (endTime - startTime) / 1000;
    return formatDuration(durationSeconds);
  };
  
  // Handle stopping a job
  const handleStopJob = async (jobId: string) => {
    try {
      await stopJob(jobId).unwrap();
      refetch();
    } catch (err) {
      console.error('Failed to stop job:', err);
    }
  };
  
  // Get paginated jobs
  const getPaginatedJobs = () => {
    if (!data?.jobs) return [];
    
    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return data.jobs.slice(startIndex, endIndex);
  };
  
  // Handle refresh button click
  const handleRefresh = () => {
    refetch();
    if (onRefresh) {
      onRefresh();
    }
  };
  
  return (
    <Card shadow="sm" radius="md" p="md" withBorder>
      <Stack spacing="md">
        <Group position="apart">
          <Text weight={500} size="lg">Ingestion Jobs</Text>
          <ActionIcon onClick={handleRefresh} loading={isLoading}>
            <IconRefresh size={16} />
          </ActionIcon>
        </Group>
        
        {isLoading && (
          <Group position="center" py="xl">
            <Loader />
            <Text>Loading jobs...</Text>
          </Group>
        )}
        
        {error && (
          <Alert color="red" title="Error" icon={<IconX size={16} />}>
            Failed to load ingestion jobs. Please try again.
          </Alert>
        )}
        
        {!isLoading && !error && data?.jobs && data.jobs.length === 0 && (
          <Text color="dimmed" align="center" py="md">
            No ingestion jobs found.
          </Text>
        )}
        
        {!isLoading && !error && data?.jobs && data.jobs.length > 0 && (
          <>
            <Table striped highlightOnHover>
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Repository</th>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Duration</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {getPaginatedJobs().map((job) => (
                  <tr key={job.job_id}>
                    <td>
                      <Text size="sm" tt="monospace">
                        {job.job_id.substring(0, 8)}...
                      </Text>
                    </td>
                    <td>
                      <Text size="sm" style={{ wordBreak: 'break-all' }}>
                        {job.repository_path}
                      </Text>
                    </td>
                    <td>
                      <Badge 
                        color={getStatusColor(job.status)}
                        variant="filled"
                        leftSection={getStatusIcon(job.status)}
                      >
                        {job.status}
                      </Badge>
                    </td>
                    <td>
                      <Text size="sm">
                        {job.started_at ? formatDate(job.started_at) : 'Not started'}
                      </Text>
                    </td>
                    <td>
                      <Text size="sm">
                        {getJobDuration(job)}
                      </Text>
                    </td>
                    <td>
                      <Menu position="bottom-end" shadow="md">
                        <Menu.Target>
                          <ActionIcon>
                            <IconDotsVertical size={16} />
                          </ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item 
                            icon={<IconEye size={16} />}
                            onClick={() => onViewDetails?.(job.job_id)}
                          >
                            View Details
                          </Menu.Item>
                          {(job.status === 'running' || job.status === 'pending') && (
                            <Menu.Item 
                              icon={<IconStop size={16} />}
                              onClick={() => handleStopJob(job.job_id)}
                              disabled={isStopping}
                              color="red"
                            >
                              Stop Job
                            </Menu.Item>
                          )}
                        </Menu.Dropdown>
                      </Menu>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
            
            {data.jobs.length > itemsPerPage && (
              <Pagination
                total={Math.ceil(data.jobs.length / itemsPerPage)}
                page={page}
                onChange={setPage}
                position="right"
              />
            )}
          </>
        )}
      </Stack>
    </Card>
  );
};

export default JobsList;