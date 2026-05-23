import { httpGet, httpPost, httpDelete } from '../request';
import request from '../request';

// ── Types ──────────────────────────────────────────────────────────────

export interface KeywordGroup {
  id: number;
  name: string;
  description: string;
  color: string;
  sort_order: number;
  keyword_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Keyword {
  id: number;
  group_id: number | null;
  keyword: string;
  platform: string;
  source: string; // manual / fission / ai
  status: string; // pending / crawled / has_results / no_results
  crawled_count: number;
  results_count: number;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface FissionResult {
  seed_keyword: string;
  platform: string;
  generated: Array<{ keyword: string; category: string; reason: string }>;
}

export interface KeywordStats {
  total_keywords: number;
  by_group: Array<{ group_name: string; count: number }>;
  by_status: Array<{ status: string; count: number }>;
  top_performing: Array<{ keyword: string; results_count: number; crawled_count: number }>;
}

export interface KeywordListResponse {
  items: Keyword[];
  total: number;
  page: number;
  page_size: number;
}

// ── Group APIs ─────────────────────────────────────────────────────────

export function fetchKeywordGroups() {
  return httpGet<KeywordGroup[]>('/api/keywords/groups');
}

export function createKeywordGroup(data: Partial<KeywordGroup>) {
  return httpPost<KeywordGroup>('/api/keywords/groups', data);
}

export function updateKeywordGroup(id: number, data: Partial<KeywordGroup>) {
  return request.put<KeywordGroup>(`/api/keywords/groups/${id}`, data).then((r) => r.data);
}

export function deleteKeywordGroup(id: number) {
  return httpDelete<{ status: string }>(`/api/keywords/groups/${id}`);
}

// ── Keyword APIs ───────────────────────────────────────────────────────

export function fetchKeywords(params?: Record<string, unknown>) {
  const q = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        q.set(k, String(v));
      }
    });
  }
  const qs = q.toString();
  return httpGet<KeywordListResponse>(`/api/keywords${qs ? `?${qs}` : ''}`);
}

export function createKeyword(data: Partial<Keyword>) {
  return httpPost<Keyword>('/api/keywords', data);
}

export function batchCreateKeywords(data: {
  keywords: string[];
  group_id?: number;
  platform?: string;
}) {
  return httpPost<Keyword[]>('/api/keywords/batch', data);
}

export function updateKeyword(id: number, data: Partial<Keyword>) {
  return request.put<Keyword>(`/api/keywords/${id}`, data).then((r) => r.data);
}

export function deleteKeyword(id: number) {
  return httpDelete<{ status: string }>(`/api/keywords/${id}`);
}

export function batchDeleteKeywords(ids: number[]) {
  return httpPost<{ status: string; deleted_count: number }>('/api/keywords/batch-delete', { ids });
}

// ── Fission APIs ───────────────────────────────────────────────────────

export function fissionKeywords(data: {
  seed_keyword: string;
  platform?: string;
  depth?: number;
}) {
  return httpPost<FissionResult>('/api/keywords/fission', data);
}

export function batchAcceptFission(data: {
  keywords: Array<{ keyword: string; notes?: string }>;
  group_id?: number;
  platform?: string;
}) {
  return httpPost<{ count: number }>('/api/keywords/batch', data);
}

// ── Stats APIs ─────────────────────────────────────────────────────────

export function fetchKeywordStats() {
  return httpGet<KeywordStats>('/api/keywords/stats');
}
