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
