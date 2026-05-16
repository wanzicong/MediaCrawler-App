import { httpGet } from '../request';
import type { DbPlatformMeta, DbQueryResult } from '@/types/config';

export function fetchDbPlatforms() {
  return httpGet<{ platforms: DbPlatformMeta[] }>('/api/data/db/platforms');
}

export function fetchDbData(
  platform: string,
  kind: string,
  params: { page?: number; page_size?: number; keyword?: string },
) {
  const q = new URLSearchParams();
  if (params.page) q.set('page', String(params.page));
  if (params.page_size) q.set('page_size', String(params.page_size));
  if (params.keyword) q.set('keyword', params.keyword);
  const qs = q.toString();
  return httpGet<DbQueryResult>(`/api/data/db/${platform}/${kind}${qs ? `?${qs}` : ''}`);
}
