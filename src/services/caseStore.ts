/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Minimal Typed Relational Store for Recovery Cases, Policy Evaluations, and Audit Entries.
 * Designed with a clean repository abstraction to allow swapping in-memory persistence
 * with PostgreSQL / Cloud SQL without modifying business logic.
 */

import {
  AuditLogEntry,
  CaseStatus,
  PolicyCheckResult,
  RecoveryCase,
} from '../types/recovery.ts';

export interface ICaseRepository {
  getById(id: string): Promise<RecoveryCase | null>;
  getAll(): Promise<RecoveryCase[]>;
  findByStatus(status: CaseStatus): Promise<RecoveryCase[]>;
  save(recoveryCase: RecoveryCase): Promise<RecoveryCase>;
  saveBatch(cases: RecoveryCase[]): Promise<RecoveryCase[]>;
  update(id: string, partial: Partial<RecoveryCase>): Promise<RecoveryCase | null>;
  clear(): Promise<void>;
}

export interface IAuditRepository {
  append(entry: Omit<AuditLogEntry, 'id' | 'timestamp'>): Promise<AuditLogEntry>;
  getByCaseId(caseId: string): Promise<AuditLogEntry[]>;
  getAll(): Promise<AuditLogEntry[]>;
  clear(): Promise<void>;
}

export interface IPolicyEvaluationRepository {
  saveEvaluation(caseId: string, result: PolicyCheckResult): Promise<void>;
  getLatestEvaluation(caseId: string): Promise<PolicyCheckResult | null>;
  getAllEvaluations(): Promise<Record<string, PolicyCheckResult>>;
  clear(): Promise<void>;
}

/**
 * In-Memory Typed Repository Implementation
 */
class InMemoryCaseRepository implements ICaseRepository {
  private cases: Map<string, RecoveryCase> = new Map();

  async getById(id: string): Promise<RecoveryCase | null> {
    const item = this.cases.get(id);
    return item ? JSON.parse(JSON.stringify(item)) : null;
  }

  async getAll(): Promise<RecoveryCase[]> {
    return Array.from(this.cases.values()).map((c) => JSON.parse(JSON.stringify(c)));
  }

  async findByStatus(status: CaseStatus): Promise<RecoveryCase[]> {
    return Array.from(this.cases.values())
      .filter((c) => c.currentStatus === status)
      .map((c) => JSON.parse(JSON.stringify(c)));
  }

  async save(recoveryCase: RecoveryCase): Promise<RecoveryCase> {
    const copy = JSON.parse(JSON.stringify(recoveryCase));
    copy.updatedAt = new Date().toISOString();
    this.cases.set(copy.id, copy);
    return JSON.parse(JSON.stringify(copy));
  }

  async saveBatch(cases: RecoveryCase[]): Promise<RecoveryCase[]> {
    const results: RecoveryCase[] = [];
    for (const c of cases) {
      results.push(await this.save(c));
    }
    return results;
  }

  async update(id: string, partial: Partial<RecoveryCase>): Promise<RecoveryCase | null> {
    const existing = this.cases.get(id);
    if (!existing) return null;

    const updated: RecoveryCase = {
      ...existing,
      ...partial,
      id: existing.id, // Immutable ID
      updatedAt: new Date().toISOString(),
    };
    this.cases.set(id, updated);
    return JSON.parse(JSON.stringify(updated));
  }

  async clear(): Promise<void> {
    this.cases.clear();
  }
}

class InMemoryAuditRepository implements IAuditRepository {
  private entries: AuditLogEntry[] = [];

  async append(entry: Omit<AuditLogEntry, 'id' | 'timestamp'>): Promise<AuditLogEntry> {
    const fullEntry: AuditLogEntry = {
      ...entry,
      id: `audit_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      timestamp: new Date().toISOString(),
    };
    this.entries.push(fullEntry);
    return JSON.parse(JSON.stringify(fullEntry));
  }

  async getByCaseId(caseId: string): Promise<AuditLogEntry[]> {
    return this.entries
      .filter((e) => e.caseId === caseId)
      .map((e) => JSON.parse(JSON.stringify(e)));
  }

  async getAll(): Promise<AuditLogEntry[]> {
    return this.entries.map((e) => JSON.parse(JSON.stringify(e)));
  }

  async clear(): Promise<void> {
    this.entries = [];
  }
}

class InMemoryPolicyEvaluationRepository implements IPolicyEvaluationRepository {
  private evaluations: Map<string, PolicyCheckResult> = new Map();

  async saveEvaluation(caseId: string, result: PolicyCheckResult): Promise<void> {
    this.evaluations.set(caseId, JSON.parse(JSON.stringify(result)));
  }

  async getLatestEvaluation(caseId: string): Promise<PolicyCheckResult | null> {
    const evalResult = this.evaluations.get(caseId);
    return evalResult ? JSON.parse(JSON.stringify(evalResult)) : null;
  }

  async getAllEvaluations(): Promise<Record<string, PolicyCheckResult>> {
    const obj: Record<string, PolicyCheckResult> = {};
    for (const [key, val] of this.evaluations.entries()) {
      obj[key] = JSON.parse(JSON.stringify(val));
    }
    return obj;
  }

  async clear(): Promise<void> {
    this.evaluations.clear();
  }
}

/**
 * Unified Storage Service Instance
 */
export class RecoveryStore {
  public cases: ICaseRepository;
  public audits: IAuditRepository;
  public policies: IPolicyEvaluationRepository;

  constructor(
    caseRepo?: ICaseRepository,
    auditRepo?: IAuditRepository,
    policyRepo?: IPolicyEvaluationRepository
  ) {
    this.cases = caseRepo ?? new InMemoryCaseRepository();
    this.audits = auditRepo ?? new InMemoryAuditRepository();
    this.policies = policyRepo ?? new InMemoryPolicyEvaluationRepository();
  }

  async clearAll(): Promise<void> {
    await this.cases.clear();
    await this.audits.clear();
    await this.policies.clear();
  }
}

// Global default singleton store
export const defaultRecoveryStore = new RecoveryStore();
