import React, { useState, useEffect } from 'react';
import { Box, Grid, Title, Collapse, Button, Group } from '@mantine/core';
import { IngestionPanel, JobsList, ProgressTracker } from '../components/ingest';
import { useDispatch } from 'react-redux';
import { setActivePage, addNotification } from '../store/slices/uiSlice';

/**
 * IngestionPage component for managing ingestion jobs
 */
const IngestionPage: React.FC = () => {
  const dispatch = useDispatch();
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [showNewIngestion, setShowNewIngestion] = useState(true);

  // Set active page when component mounts
  useEffect(() => {
    dispatch(setActivePage('ingest'));
  }, [dispatch]);

  // Handle viewing job details
  const handleViewDetails = (jobId: string) => {
    setSelectedJobId(jobId);
    // Collapse the new ingestion panel when viewing details
    setShowNewIngestion(false);
    // Add notification
    dispatch(addNotification({
      type: 'info',
      message: `Viewing details for job ${jobId.substring(0, 8)}...`,
      timeout: 3000
    }));
  };

  // Handle starting a new job
  const handleJobStarted = (jobId: string) => {
    // Auto-select the newly created job
    setSelectedJobId(jobId);
    // Add notification
    dispatch(addNotification({
      type: 'success',
      message: `Ingestion job ${jobId.substring(0, 8)}... started successfully`,
      timeout: 5000
    }));
  };

  // Handle closing job details
  const handleCloseDetails = () => {
    setSelectedJobId(null);
  };

  // Handle refresh from children components
  const handleRefresh = () => {
    // Any additional refresh logic can go here
  };

  return (
    <Box p="md">
      <Group position="apart" mb="md">
        <Title order={2}>Ingestion Dashboard</Title>
        <Button
          variant="subtle"
          onClick={() => setShowNewIngestion(!showNewIngestion)}
        >
          {showNewIngestion ? 'Hide New Ingestion' : 'Show New Ingestion'}
        </Button>
      </Group>

      <Grid gutter="md">
        <Grid.Col span={12}>
          <Collapse in={showNewIngestion}>
            <IngestionPanel onStarted={handleJobStarted} />
          </Collapse>
        </Grid.Col>

        <Grid.Col span={12}>
          <JobsList
            onViewDetails={handleViewDetails}
            onRefresh={handleRefresh}
          />
        </Grid.Col>

        {selectedJobId && (
          <Grid.Col span={12}>
            <ProgressTracker
              jobId={selectedJobId}
              onClose={handleCloseDetails}
            />
          </Grid.Col>
        )}
      </Grid>
    </Box>
  );
};

export default IngestionPage;