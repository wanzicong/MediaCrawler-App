import { httpDelete, httpGet, httpPost } from '../request';
import type { ApiResponse, CrawlerStartPayload, CrawlerStatusResponse } from '@/types/api';
import type { CrawlerTask, TaskListResponse, TaskRerunResponse } from '@/types/config';

export function startCrawler(payload: CrawlerStartPayload) {
  return httpPost<ApiResponse & { task_id?: number }>('/api/crawler/start', {
    ...payload,
    save_option: 'db',
  });
}

export function fetchCrawlerTasks(params: {
  page?: number;
  page_size?: number;
  status?: string;
} = {}) {
  const q = new URLSearchParams();
  if (params.page) q.set('page', String(params.page));
  if (params.page_size) q.set('page_size', String(params.page_size));
  if (params.status) q.set('status', params.status);
  const qs = q.toString();
  return httpGet<TaskListResponse>(`/api/crawler/tasks${qs ? `?${qs}` : ''}`);
}

export function fetchCrawlerTaskDetail(taskId: number) {
  return httpGet<CrawlerTask>(`/api/crawler/tasks/${taskId}`);
}

export function rerunCrawlerTask(taskId: number) {
  return httpPost<TaskRerunResponse>(`/api/crawler/tasks/${taskId}/rerun`);
}

export function stopCrawler() {
  return httpPost<ApiResponse>('/api/crawler/stop');
}

export function deleteCrawlerTask(taskId: number) {
  return httpDelete<ApiResponse>(`/api/crawler/tasks/${taskId}`);
}

export function fetchCrawlerStatus() {
  return httpGet<CrawlerStatusResponse>('/api/crawler/status');
}

export interface CrawlerLogEntry {
  id: number;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success' | 'debug';
  message: string;
}

export function fetchCrawlerLogs(limit = 200) {
  return httpGet<{ logs: CrawlerLogEntry[] }>(`/api/crawler/logs?limit=${limit}`);
}
