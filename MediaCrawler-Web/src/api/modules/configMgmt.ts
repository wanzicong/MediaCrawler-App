import { httpGet, httpPost } from '../request';
import type { CrawlerPayload, CrawlerProfile } from '@/types/config';

export function fetchProfiles() {
  return httpGet<CrawlerProfile[]>('/api/config/profiles');
}

export function fetchProfile(id: number) {
  return httpGet<CrawlerProfile>(`/api/config/profiles/${id}`);
}

export function createProfile(body: {
  name: string;
  description?: string;
  is_default?: boolean;
  payload: CrawlerPayload;
}) {
  return httpPost<CrawlerProfile>('/api/config/profiles', body);
}

export async function putProfile(
  id: number,
  body: {
    name?: string;
    description?: string;
    is_default?: boolean;
    payload?: CrawlerPayload;
  },
) {
  const request = (await import('../request')).default;
  const { data } = await request.put<CrawlerProfile>(`/api/config/profiles/${id}`, body);
  return data;
}

export async function deleteProfile(id: number) {
  const request = (await import('../request')).default;
  const { data } = await request.delete<{ status: string }>(`/api/config/profiles/${id}`);
  return data;
}

export function setDefaultProfile(id: number) {
  return httpPost<CrawlerProfile>(`/api/config/profiles/${id}/default`);
}
