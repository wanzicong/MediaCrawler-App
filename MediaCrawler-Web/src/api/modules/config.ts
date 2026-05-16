import { httpGet } from '../request';
import type { ConfigOptionsResponse, PlatformItem } from '@/types/api';

export function fetchPlatforms() {
  return httpGet<{ platforms: PlatformItem[] }>('/api/config/platforms');
}

export function fetchConfigOptions() {
  return httpGet<ConfigOptionsResponse>('/api/config/options');
}
