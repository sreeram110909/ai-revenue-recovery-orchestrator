/**
 * API Service for Backend Communication
 * Consumes FastAPI endpoints without any direct financial/secret handling in the browser.
 */

import {
  CaseDetailResponse,
  CaseListResponse,
  BatchRunSummary,
  HealthCheckResponse,
  RecoveryCase,
} from '../types/api';

const API_BASE = '';

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      let errorDetail = response.statusText;
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.detail || errorDetail;
      } catch {
        // use fallback statusText
      }
      throw new ApiError(`API Request failed (${response.status}): ${errorDetail}`, response.status, errorDetail);
    }

    return await response.json();
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(`Network error connecting to backend: ${err.message || 'Server unreachable'}`);
  }
}

export const api = {
  /**
   * Healthcheck endpoint
   */
  async getHealth(): Promise<HealthCheckResponse> {
    return fetchJson<HealthCheckResponse>('/health');
  },

  /**
   * List recovery cases with optional filtering
   */
  async getCases(params?: {
    status?: string;
    case_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<CaseListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.case_type) query.set('case_type', params.case_type);
    if (params?.limit) query.set('limit', params.limit.toString());
    if (params?.offset) query.set('offset', params.offset.toString());

    const qs = query.toString() ? `?${query.toString()}` : '';
    return fetchJson<CaseListResponse>(`/api/v1/cases${qs}`);
  },

  /**
   * Retrieve single recovery case and its immutable audit trail
   */
  async getCase(caseId: string): Promise<CaseDetailResponse> {
    return fetchJson<CaseDetailResponse>(`/api/v1/cases/${encodeURIComponent(caseId)}`);
  },

  /**
   * Execute LangGraph recovery workflow on a case (blocking POST)
   */
  async processCase(caseId: string): Promise<{
    status: string;
    case_id: string;
    final_status: string;
    verified_recovered_amount: number;
    case: RecoveryCase;
    audit_events: string[];
  }> {
    return fetchJson(`/api/v1/cases/${encodeURIComponent(caseId)}/process`, {
      method: 'POST',
    });
  },

  /**
   * Execute LangGraph recovery workflow with real-time SSE progress streaming.
   */
  streamProcessCase(
    caseId: string,
    onStep: (data: {
      event: string;
      step_key?: string;
      step_index?: number;
      step_name?: string;
      status?: string;
      detail?: string;
      case?: RecoveryCase;
      final_status?: string;
      verified_recovered_amount?: number;
      audit_events?: string[];
      error?: string;
    }) => void,
    onError: (err: Error) => void,
    onComplete: (data?: any) => void
  ): () => void {
    const url = `/api/v1/cases/${encodeURIComponent(caseId)}/process/stream`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === 'step_progress') {
          onStep(payload);
        } else if (payload.event === 'complete') {
          onComplete(payload);
          eventSource.close();
        } else if (payload.event === 'error') {
          onError(new Error(payload.error || 'Stream error occurred'));
          eventSource.close();
        }
      } catch (err: any) {
        console.error('Failed to parse SSE payload:', err);
      }
    };

    eventSource.onerror = (err) => {
      eventSource.close();
      onError(new Error('SSE connection closed or lost'));
    };

    return () => {
      eventSource.close();
    };
  },

  /**
   * Get latest batch evaluation metrics and baseline comparison
   */
  async getBatchMetrics(): Promise<BatchRunSummary> {
    return fetchJson<BatchRunSummary>('/api/v1/metrics/batch');
  },

  /**
   * Trigger a new 3-way evaluation benchmark run
   */
  async runBatch(params?: {
    seed?: number;
    count?: number;
    dataset_version?: string;
  }): Promise<BatchRunSummary> {
    return fetchJson<BatchRunSummary>('/api/v1/batch/run', {
      method: 'POST',
      body: JSON.stringify(params || { seed: 42, count: 60, dataset_version: 'v1.0' }),
    });
  },

  /**
   * Ingest cases into the system
   */
  async ingestCases(cases: Partial<RecoveryCase>[]): Promise<{
    status: string;
    ingested_count: number;
    case_ids: string[];
  }> {
    return fetchJson('/api/v1/cases/ingest', {
      method: 'POST',
      body: JSON.stringify({ cases }),
    });
  },
};
