import { httpDelete, httpGet, httpPost } from '../request';
import type { ApiResponse } from '@/types/api';

export interface CommentSyncRequest {
  platform: string;
  post_id?: string;
  post_url?: string;
  max_comments?: number;
  crawl_replies?: boolean;
}

export interface CommentAsyncRequest extends CommentSyncRequest {
  priority?: string;
}

export interface CommentBatchRequest {
  platform: string;
  posts: { post_id?: string; post_url?: string }[];
  max_comments?: number;
  crawl_replies?: boolean;
}

export interface CommentTask {
  task_id: string;
  platform: string;
  post_id: string;
  status: string;
  progress: number;
  total_crawled: number;
  comments?: any[];
  error: string;
  created_at: string;
  finished_at: string;
}

export interface RateLimitStatus {
  [platform: string]: {
    rate_per_min: number;
    available: number;
    max_burst: number;
    used_slots: number;
    max_slots: number;
  };
}

export function commentSync(params: CommentSyncRequest) {
  return httpPost<any>('/api/crawler-pro/comments/sync', params);
}

export function commentAsync(params: CommentAsyncRequest) {
  return httpPost<{ status: string; task_id: string }>('/api/crawler-pro/comments/async', params);
}

export function commentBatch(params: CommentBatchRequest) {
  return httpPost<{ status: string; count: number; task_ids: string[] }>(
    '/api/crawler-pro/comments/batch', params,
  );
}

export function fetchCommentTasks(limit = 50) {
  return httpGet<{ total: number; tasks: CommentTask[] }>(
    `/api/crawler-pro/comments/tasks?limit=${limit}`,
  );
}

export function fetchCommentTask(taskId: string) {
  return httpGet<CommentTask>(`/api/crawler-pro/comments/tasks/${taskId}`);
}

export function deleteCommentTask(taskId: string) {
  return httpDelete<ApiResponse>(`/api/crawler-pro/comments/tasks/${taskId}`);
}

export function fetchRateLimitStatus() {
  return httpGet<RateLimitStatus>('/api/crawler-pro/comments/rate-limit-status');
}
