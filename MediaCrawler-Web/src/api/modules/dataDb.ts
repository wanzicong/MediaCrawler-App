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
  if (params.page != null) q.set('page', String(params.page));
  if (params.page_size != null) q.set('page_size', String(params.page_size));
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
  if (params.page != null) q.set('page', String(params.page));
  if (params.page_size != null) q.set('page_size', String(params.page_size));
  if (params.order_by) q.set('order_by', params.order_by);
  if (params.order_direction) q.set('order_direction', params.order_direction);
  const qs = q.toString();
  return httpGet<DbQueryResult>(`/api/data/db/${platform}/task/${taskId}${qs ? `?${qs}` : ''}`);
}

export function fetchContentComments(
  platform: string,
  contentId: string,
  params: { page?: number; page_size?: number; order_by?: string; order_direction?: string },
) {
  const q = new URLSearchParams();
  if (params.page != null) q.set('page', String(params.page));
  if (params.page_size != null) q.set('page_size', String(params.page_size));
  if (params.order_by) q.set('order_by', params.order_by);
  if (params.order_direction) q.set('order_direction', params.order_direction);
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

// ── 内容邻居（上一条/下一条）────────────────────────────────────────

export interface ContentNeighbors {
  platform: string;
  kind: string;
  current_content_id: string;
  prev: Record<string, unknown> | null;
  next: Record<string, unknown> | null;
}

export function fetchContentNeighbors(
  platform: string,
  params: {
    content_id: string;
    order_by?: string;
    order_direction?: string;
    keyword?: string;
    task_id?: number;
  },
) {
  const q = new URLSearchParams();
  q.set('content_id', params.content_id);
  if (params.order_by) q.set('order_by', params.order_by);
  if (params.order_direction) q.set('order_direction', params.order_direction);
  if (params.keyword) q.set('keyword', params.keyword);
  if (params.task_id != null) q.set('task_id', String(params.task_id));
  return httpGet<ContentNeighbors>(`/api/data/db/${platform}/contents/neighbors?${q.toString()}`);
}
