import { httpGet, httpPost } from '../request';

export function fetchDatabaseStatus() {
  return httpGet<{ connected: boolean; host?: string; database?: string; error?: string }>(
    '/api/system/database/status',
  );
}

export function initDatabase() {
  return httpPost<{ success: boolean; message: string }>('/api/system/init-database');
}
