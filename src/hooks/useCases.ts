import { useState, useEffect, useCallback } from 'react';
import { RecoveryCase } from '../types/api';
import { api, ApiError } from '../services/api';

export interface UseCasesParams {
  status?: string;
  case_type?: string;
  limit?: number;
  offset?: number;
}

export function useCases(initialParams?: UseCasesParams) {
  const [cases, setCases] = useState<RecoveryCase[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [params, setParams] = useState<UseCasesParams>(initialParams || { limit: 100, offset: 0 });

  const fetchCases = useCallback(async (queryParams?: UseCasesParams) => {
    setLoading(true);
    setError(null);
    try {
      const activeParams = queryParams || params;
      const res = await api.getCases(activeParams);
      setCases(res.cases);
      setTotal(res.total);
    } catch (err: any) {
      setError(err instanceof ApiError ? err.message : 'Failed to fetch cases');
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    fetchCases(params);
  }, [params, fetchCases]);

  const updateFilters = (newParams: Partial<UseCasesParams>) => {
    setParams(prev => ({ ...prev, ...newParams }));
  };

  return {
    cases,
    total,
    loading,
    error,
    params,
    updateFilters,
    refetch: () => fetchCases(params),
  };
}
