import { useState, useEffect, useCallback } from 'react';
import { RecoveryCase, AuditLogEntry } from '../types/api';
import { api, ApiError } from '../services/api';

export function useCase(caseId: string | undefined) {
  const [caseData, setCaseData] = useState<RecoveryCase | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [processing, setProcessing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCase = useCallback(async () => {
    if (!caseId) {
      setCaseData(null);
      setAuditTrail([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await api.getCase(caseId);
      setCaseData(res.case);
      setAuditTrail(res.audit_trail);
    } catch (err: any) {
      setError(err instanceof ApiError ? err.message : `Failed to load case '${caseId}'`);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  const processCase = useCallback(async () => {
    if (!caseId) return;
    setProcessing(true);
    setError(null);
    try {
      const res = await api.processCase(caseId);
      setCaseData(res.case);
      // Refresh audit trail
      const updated = await api.getCase(caseId);
      setAuditTrail(updated.audit_trail);
      return res;
    } catch (err: any) {
      setError(err instanceof ApiError ? err.message : `Failed to process workflow for case '${caseId}'`);
      throw err;
    } finally {
      setProcessing(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchCase();
  }, [fetchCase]);

  return {
    caseData,
    auditTrail,
    loading,
    processing,
    error,
    refetch: fetchCase,
    processCase,
  };
}
