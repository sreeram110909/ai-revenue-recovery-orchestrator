import { useState, useEffect, useCallback } from 'react';
import { BatchRunSummary } from '../types/api';
import { api, ApiError } from '../services/api';

export function useMetrics() {
  const [data, setData] = useState<BatchRunSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await api.getBatchMetrics();
      setData(summary);
    } catch (err: any) {
      setError(err instanceof ApiError ? err.message : 'Failed to fetch evaluation metrics');
    } finally {
      setLoading(false);
    }
  }, []);

  const runBenchmark = useCallback(async (params?: { seed?: number; count?: number; dataset_version?: string }) => {
    setRunning(true);
    setError(null);
    try {
      const summary = await api.runBatch(params);
      setData(summary);
      return summary;
    } catch (err: any) {
      setError(err instanceof ApiError ? err.message : 'Failed to run benchmark');
      throw err;
    } finally {
      setRunning(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return {
    metrics: data,
    loading,
    running,
    error,
    refetch: fetchMetrics,
    runBenchmark,
  };
}
