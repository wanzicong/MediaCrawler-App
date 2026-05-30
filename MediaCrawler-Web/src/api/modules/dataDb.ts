import { httpDelete, httpGet } from '../request';
import type { DbPlatformMeta, DbQueryResult, TaskDataStats } from '@/types/config';

export function fetchDbPlatforms() {
  return httpGet<{ platforms: DbPlatformMeta[] }>('/api/data/db/platforms');
}

export function fetchDbData(
  platform: string,
  kind: string,
  params: { page?: number; page_size?: number; keyword?: string; content_id?: string; order_by?: string; order_direction?: string },
) {
  const q = new URLSearchParams();
  if (params.page) q.set('page', String(params.page));
  if (params.page_size) q.set('page_size', String(params.page_size));
  if (params.keyword) q.set('keyword', params.keyword);
  if (params.content_id) q.set('content_id', params.content_id);
  if (params.order_by) q.set('order_by', params.order_by);
  if (params.order_direction) q.set('order_direction', params.order_direction);
  const qs = q.toString();
  return httpGet<DbQueryResult>(`/api/data/db/${platform}/${kind}${qs ? `?${qs}` : ''}`);
}

export function fetchTaskData(
  platform: string,
  taskId: number,
  params: { page?: number; page_size?: number; order_by?: string; order_direction?: string },
) {
  const q = new URLSearchParams();
  if (params.page) q.set('page', String(params.page));
  if (params.page_size) q.set('page_size', String(params.page_size));
  if (params.order_by) q.set('order_by', params.order_by);
  if (params.order_direction) q.set('order_direction', params.order_direction);
  const qs = q.toString();
  return httpGet<DbQueryResult>(`/api/data/db/${platform}/task/${taskId}${qs ? `?${qs}` : ''}`);
}

export function fetchContentComments(
  platform: string,
  contentId: string,
  params: { page?: number; page_size?: number },
) {
  const q = new URLSearchParams();
  if (params.page) q.set('page', String(params.page));
  if (params.page_size) q.set('page_size', String(params.page_size));
  const qs = q.toString();
  return httpGet<DbQueryResult>(`/api/data/db/${platform}/comments/content/${contentId}${qs ? `?${qs}` : ''}`);
}

export function deleteDataRecord(platform: string, kind: string, recordId: number) {
  return httpDelete<{ status: string; message: string }>(`/api/data/db/${platform}/${kind}/${recordId}`);
}

export function fetchTaskDataStats(taskId: number) {
  return httpGet<TaskDataStats>(`/api/data/db/task/${taskId}/stats`);
}

export interface TaskInfo {
  task_id: number;
  keywords: string;
  status: string;
  created_at: string;
  record_count: number;
}

export function fetchAvailableTasks(platform: string, kind: string) {
  return httpGet<TaskInfo[]>(`/api/data/db/${platform}/${kind}/tasks`);
}
