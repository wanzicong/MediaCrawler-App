import { httpGet } from '../request';
import type { EnvCheckResponse, HealthResponse } from '@/types/api';

export function fetchHealth() {
  return httpGet<HealthResponse>('/api/health');
}

export function fetchEnvCheck() {
  return httpGet<EnvCheckResponse>('/api/env/check');
}
