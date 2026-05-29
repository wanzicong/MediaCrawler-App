import { httpDelete, httpGet, httpPost } from '../request';
import type { ApiResponse } from '@/types/api';

// ==================== 多任务调度 ====================

export interface ProSchedulerStatus {
  max_concurrent: number;
  running_count: number;
  waiting_count: number;
  platform_running: Record<string, number>;
  running: { task_id: number; platform: string }[];
  waiting: { task_id: number; platform: string; priority: number }[];
}

export function fetchProStatus() {
  return httpGet<ProSchedulerStatus>('/api/crawler-pro/status');
}

export function startProCrawler(params: {
  platform: string;
  keywords: string;
  crawler_type: string;
  priority?: string;
  resume?: boolean;
  headless?: boolean;
}) {
  return httpPost<{ status: string; task_id: number; priority: string; resume: boolean }>(
    `/api/crawler-pro/start?priority=${params.priority || 'normal'}&resume=${params.resume ?? true}`,
    params,
  );
}

export function stopProCrawler(taskId: number) {
  return httpPost<ApiResponse>(`/api/crawler-pro/stop/${taskId}`);
}

export function setMaxConcurrent(count: number) {
  return httpPost<{ status: string; max_concurrent: number }>(
    `/api/crawler-pro/config/max-concurrent?count=${count}`,
  );
}

// ==================== 断点续爬 ====================

export interface CheckpointData {
  task_id: number;
  platform: string;
  crawler_type: string;
  keywords: string;
  current_page: number;
  total_crawled: number;
  crawled_note_ids: string[];
  last_cursor?: string;
  status: string;
}

export function fetchCheckpoint(taskId: number) {
  return httpGet<{ status: string; task_id: number; checkpoint: CheckpointData | null }>(
    `/api/crawler-pro/checkpoint/${taskId}`,
  );
}

export function deleteCheckpoint(taskId: number) {
  return httpDelete<ApiResponse>(`/api/crawler-pro/checkpoint/${taskId}`);
}

// ==================== 多账号管理 ====================

export interface AccountInfo {
  id: number;
  platform: string;
  username: string;
  status: string;
  daily_requests: number;
}

export interface AccountListResponse {
  platform: string;
  total_accounts: number;
  available: number;
  accounts: AccountInfo[];
  current: AccountInfo | null;
}

export function fetchAccounts(platform: string) {
  return httpGet<AccountListResponse>(`/api/crawler-pro/accounts/${platform}`);
}

export function refreshAccounts(platform: string) {
  return httpPost<{ status: string; platform: string; accounts_loaded: number }>(
    `/api/crawler-pro/accounts/${platform}/refresh`,
  );
}

// ==================== Pro 配置 ====================

export interface ProConfig {
  max_concurrent: number;
  per_platform_queue: boolean;
  features: Record<string, boolean>;
}

export function fetchProConfig() {
  return httpGet<ProConfig>('/api/crawler-pro/config');
}
