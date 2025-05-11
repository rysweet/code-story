import { useState, useCallback, useEffect } from 'react';
import { 
  useStartIngestionMutation, 
  useStopIngestionMutation,
  useGetIngestionStatusQuery,
  IngestionJob
} from '../store';
import useWebSocket from './useWebSocket';

/**
 * Progress update from WebSocket
 */
interface ProgressUpdate {
  job_id: string;
  step_id?: string;
  step_name?: string;
  progress: number;
  status: string;
  message?: string;
}

/**
 * Hook for managing ingestion operations and progress tracking
 * @param jobId - Optional ingestion job ID to track
 * @returns Ingestion state and control functions
 */
export function useIngest(jobId?: string) {
  const [startIngestion, { isLoading: isStarting }] = useStartIngestionMutation();
  const [stopIngestion, { isLoading: isStopping }] = useStopIngestionMutation();
  const { data: jobStatus, refetch } = useGetIngestionStatusQuery(jobId || '', { 
    skip: !jobId,
    pollingInterval: 5000, // Fallback polling if WebSocket fails
  });

  const [currentJobId, setCurrentJobId] = useState<string | null>(jobId || null);
  const [progressData, setProgressData] = useState<ProgressUpdate | null>(null);

  // WebSocket connection for real-time progress updates
  const { 
    isConnected: isWsConnected, 
    message: wsMessage,
  } = useWebSocket<ProgressUpdate | null>(
    currentJobId ? `/status/${currentJobId}` : '', 
    null
  );

  // Update progress data when WebSocket message is received
  useEffect(() => {
    if (wsMessage && currentJobId) {
      setProgressData(wsMessage);
    }
  }, [wsMessage, currentJobId]);

  // Start a new ingestion job
  const startJob = useCallback(async (repositoryPath: string, options?: Record<string, any>) => {
    try {
      const result = await startIngestion({ 
        repository_path: repositoryPath,
        options 
      }).unwrap();
      
      setCurrentJobId(result.job_id);
      return result.job_id;
    } catch (error) {
      console.error('Failed to start ingestion', error);
      throw error;
    }
  }, [startIngestion]);

  // Stop an active ingestion job
  const stopJob = useCallback(async (jobIdToStop?: string) => {
    const idToStop = jobIdToStop || currentJobId;
    if (!idToStop) {
      throw new Error('No job ID provided to stop');
    }
    
    try {
      const result = await stopIngestion(idToStop).unwrap();
      return result.success;
    } catch (error) {
      console.error('Failed to stop ingestion', error);
      throw error;
    }
  }, [stopIngestion, currentJobId]);

  // Get the current job progress, either from WebSocket or API
  const getJobProgress = useCallback((): { 
    progress: number;
    status: string;
    isLive: boolean;
  } => {
    if (progressData) {
      return {
        progress: progressData.progress,
        status: progressData.status,
        isLive: true,
      };
    }
    
    if (jobStatus) {
      // Calculate progress from job steps if available
      let totalProgress = 0;
      if (jobStatus.steps && jobStatus.steps.length > 0) {
        totalProgress = jobStatus.steps.reduce(
          (sum, step) => sum + step.progress, 
          0
        ) / jobStatus.steps.length;
      }
      
      return {
        progress: totalProgress,
        status: jobStatus.status,
        isLive: false,
      };
    }
    
    return {
      progress: 0,
      status: 'unknown',
      isLive: false,
    };
  }, [progressData, jobStatus]);

  return {
    startJob,
    stopJob,
    getJobProgress,
    isStarting,
    isStopping,
    jobId: currentJobId,
    jobStatus,
    progressData,
    isWsConnected,
    refetchStatus: refetch,
  };
}

export default useIngest;