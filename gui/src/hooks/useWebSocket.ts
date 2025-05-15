import { useState, useEffect, useCallback, useRef } from 'react';
import { createWebSocket } from '../utils/api';

/**
 * Hook for WebSocket communication
 * @param path - WebSocket path (e.g., '/status/123')
 * @param initialValue - Initial value for the message state
 * @returns WebSocket state and control functions
 */
export function useWebSocket<T>(path: string, initialValue: T) {
  const [isConnected, setIsConnected] = useState(false);
  const [message, setMessage] = useState<T>(initialValue);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Connect to WebSocket
  const connect = useCallback(() => {
    try {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        return;
      }

      const ws = createWebSocket(path);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setMessage(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message', err);
          setError('Failed to parse WebSocket message');
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error', event);
        setError('WebSocket connection error');
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Try to reconnect after a delay
        setTimeout(() => {
          if (wsRef.current?.readyState !== WebSocket.OPEN) {
            connect();
          }
        }, 3000);
      };
    } catch (err) {
      console.error('Failed to connect to WebSocket', err);
      setError('Failed to connect to WebSocket');
      setIsConnected(false);
    }
  }, [path]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setIsConnected(false);
    }
  }, []);

  // Send a message through the WebSocket
  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      setError('WebSocket is not connected');
    }
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    message,
    error,
    send,
    connect,
    disconnect,
  };
}

export default useWebSocket;