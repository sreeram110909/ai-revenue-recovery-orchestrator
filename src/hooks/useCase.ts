import { useState, useEffect, useCallback } from 'react';
import { RecoveryCase, AuditLogEntry } from '../types/api';
import { api, ApiError } from '../services/api';

export function useCase(caseId: string | undefined) {
  const [caseData, setCaseData] = useState<RecoveryCase | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [processing, setProcessing] = useState<boolean>(false);
  const [activeStepKey, setActiveStepKey] = useState<string | null>(null);
  const [completedStepKeys, setCompletedStepKeys] = useState<string[]>([]);
  const [streamingStatus, setStreamingStatus] = useState<string | null>(null);
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

  const processCaseStream = useCallback(async () => {
    if (!caseId || processing) return;
    setProcessing(true);
    setError(null);
    setActiveStepKey('detect_and_load');
    setCompletedStepKeys([]);
    setStreamingStatus('Initializing LangGraph stream...');

    return new Promise<{ status: string; case: RecoveryCase }>((resolve, reject) => {
      let resolved = false;

      // Safe timeout fallback: if stream disconnects, recover via GET /cases/{id}
      const timeoutId = setTimeout(async () => {
        if (!resolved) {
          resolved = true;
          try {
            const fallback = await api.getCase(caseId);
            setCaseData(fallback.case);
            setAuditTrail(fallback.audit_trail);
            setProcessing(false);
            setActiveStepKey(null);
            setStreamingStatus(null);
            resolve({ status: 'success', case: fallback.case });
          } catch (err: any) {
            setProcessing(false);
            setActiveStepKey(null);
            setStreamingStatus(null);
            reject(err);
          }
        }
      }, 15000);

      const stepOrder = [
        'detect_and_load',
        'extract_evidence',
        'diagnose',
        'score_strategy',
        'evaluate_policy',
        'execute_action',
        'verify_outcome',
      ];

      api.streamProcessCase(
        caseId,
        (eventData) => {
          if (eventData.step_key) {
            setCompletedStepKeys((prev) => Array.from(new Set([...prev, eventData.step_key!])));
            const currentIdx = stepOrder.indexOf(eventData.step_key);
            if (currentIdx !== -1 && currentIdx + 1 < stepOrder.length) {
              setActiveStepKey(stepOrder[currentIdx + 1]);
            }
            setStreamingStatus(`Completed ${eventData.step_name}`);
            if (eventData.case) {
              setCaseData(eventData.case);
            }
          }
        },
        async (streamErr) => {
          if (!resolved) {
            resolved = true;
            clearTimeout(timeoutId);
            // Fallback gracefully on stream disruption
            try {
              const fallback = await api.getCase(caseId);
              setCaseData(fallback.case);
              setAuditTrail(fallback.audit_trail);
              setProcessing(false);
              setActiveStepKey(null);
              setStreamingStatus(null);
              resolve({ status: 'success', case: fallback.case });
            } catch (err: any) {
              setError(err instanceof ApiError ? err.message : streamErr.message);
              setProcessing(false);
              setActiveStepKey(null);
              setStreamingStatus(null);
              reject(streamErr);
            }
          }
        },
        async (completeData) => {
          if (!resolved) {
            resolved = true;
            clearTimeout(timeoutId);
            try {
              if (completeData?.case) {
                setCaseData(completeData.case);
              }
              const updated = await api.getCase(caseId);
              setCaseData(updated.case);
              setAuditTrail(updated.audit_trail);
              setProcessing(false);
              setActiveStepKey(null);
              setStreamingStatus(null);
              resolve({
                status: 'success',
                case: updated.case,
              });
            } catch (err: any) {
              setProcessing(false);
              setActiveStepKey(null);
              setStreamingStatus(null);
              reject(err);
            }
          }
        }
      );
    });
  }, [caseId, processing]);

  useEffect(() => {
    fetchCase();
  }, [fetchCase]);

  return {
    caseData,
    auditTrail,
    loading,
    processing,
    activeStepKey,
    completedStepKeys,
    streamingStatus,
    error,
    refetch: fetchCase,
    processCase,
    processCaseStream,
  };
}
