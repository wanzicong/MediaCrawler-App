import { httpGet, httpPost, httpDelete } from '../request';
import request from '../request';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  session_id?: number | null;
  messages: ChatMessage[];
  model?: string;
}

export interface ChatResponse {
  content: string;
  model: string;
  session_id: number;
}

export interface SessionInfo {
  id: number;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface MemoryInfo {
  id: number;
  key: string;
  content: string;
  category: string;
  created_at: string;
  updated_at: string;
}

export function sendChatMessage(data: ChatRequest) {
  return httpPost<ChatResponse>('/api/ai/chat', data);
}

export function fetchSessions() {
  return httpGet<SessionInfo[]>('/api/ai/sessions');
}

export function fetchSession(id: number) {
  return httpGet<SessionInfo>(`/api/ai/sessions/${id}`);
}

export function createSession(title: string) {
  return httpPost<SessionInfo>('/api/ai/sessions', { title });
}

export function renameSession(id: number, title: string) {
  return request.put(`/api/ai/sessions/${id}`, { title });
}

export function deleteSession(id: number) {
  return httpDelete(`/api/ai/sessions/${id}`);
}

export function fetchSessionMessages(sessionId: number) {
  return httpGet<{ session_id: number; messages: ChatMessage[] }>(
    `/api/ai/sessions/${sessionId}/messages`
  );
}

export function fetchMemories() {
  return httpGet<MemoryInfo[]>('/api/ai/memories');
}

export function createMemory(key: string, content: string, category?: string) {
  return httpPost<MemoryInfo>('/api/ai/memories', { key, content, category: category || '通用' });
}

export function deleteMemory(id: number) {
  return httpDelete(`/api/ai/memories/${id}`);
}

export interface AnalyzeRequest {
  platform: string;
  content_id: string;
}

export interface SentimentResult {
  positive: number;
  neutral: number;
  negative: number;
  summary: string;
}

export interface KeyInsight {
  point: string;
  representative_comment: string;
}

export interface AnalyzeResponse {
  platform: string;
  content_id: string;
  comment_count: number;
  sentiment: SentimentResult;
  key_insights: KeyInsight[];
  summary: string;
  hot_topics: string[];
}

export function analyzeComments(data: AnalyzeRequest, signal?: AbortSignal) {
  return httpPost<AnalyzeResponse>('/api/ai/analyze-comments', data, { signal });
}

// ── Batch Analyze ──────────────────────────────────────────────

export interface BatchAnalyzeRequest {
  platform: string;
  max_articles?: number;
}

export interface ArticleInsight {
  title: string;
  comment_count: number;
  insight: string;
}

export interface BatchAnalyzeResponse {
  platform: string;
  article_count: number;
  total_comment_count: number;
  overall_summary: string;
  key_themes: string[];
  sentiment: SentimentResult;
  article_insights: ArticleInsight[];
  suggestions: string[];
}

export function batchAnalyze(data: BatchAnalyzeRequest, signal?: AbortSignal) {
  return httpPost<BatchAnalyzeResponse>('/api/ai/batch-analyze', data, { signal });
}
