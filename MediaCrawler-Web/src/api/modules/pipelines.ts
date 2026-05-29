import { httpDelete, httpGet, httpPost } from '../request';
import type { ApiResponse } from '@/types/api';

export interface PipelineCreateRequest {
  name: string;
  platform: string;
  keywords: string[];
  mode: 'batch' | 'queue' | 'cron';
  config?: Record<string, any>;
}

export interface PipelineItem {
  pipeline_id: string;
  name: string;
  platform: string;
  keywords_count: number;
  mode: string;
  status: string;
  progress: number;
  total: number;
  created_at: string;
}

export interface PipelineDetail extends PipelineItem {
  tasks: {
    ref: string;
    keyword: string;
    status: string;
    task_id: number | null;
    error: string;
  }[];
}

// Keyword run
export interface KeywordRunResponse {
  status: string;
  keyword_id: number;
  keyword: string;
  platform: string;
  task_id: number;
}

export interface KeywordTasksResponse {
  keyword_id: number;
  keyword: string;
  tasks: { task_id: number; status: string; created_at: string; finished_at: string }[];
}

export function createPipeline(params: PipelineCreateRequest) {
  return httpPost<PipelineItem & { pipeline_id: string }>('/api/crawler-pro/pipelines', params);
}

export function fetchPipelines() {
  return httpGet<{ pipelines: PipelineItem[] }>('/api/crawler-pro/pipelines');
}

export function fetchPipeline(pipelineId: string) {
  return httpGet<PipelineDetail>(`/api/crawler-pro/pipelines/${pipelineId}`);
}

export function runPipeline(pipelineId: string) {
  return httpPost<{ status: string; pipeline_id: string; mode: string }>(
    `/api/crawler-pro/pipelines/${pipelineId}/run`,
  );
}

export function stopPipeline(pipelineId: string) {
  return httpPost<ApiResponse>(`/api/crawler-pro/pipelines/${pipelineId}/stop`);
}

export function deletePipeline(pipelineId: string) {
  return httpDelete<ApiResponse>(`/api/crawler-pro/pipelines/${pipelineId}`);
}

export function keywordRun(keywordId: number) {
  return httpPost<KeywordRunResponse>(`/api/keywords/run`, { keyword_id: keywordId });
}

export function keywordsBatchRun(ids: number[], mode: string = 'batch') {
  return httpPost<{ total_keywords: number; pipelines: any[] }>('/api/keywords/batch-run', { ids, mode });
}

export function fetchKeywordTasks(keywordId: number) {
  return httpGet<KeywordTasksResponse>(`/api/keywords/${keywordId}/tasks`);
}
