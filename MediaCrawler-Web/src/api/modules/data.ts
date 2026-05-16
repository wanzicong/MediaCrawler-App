import { httpGet } from '../request';
import type { DataFileItem } from '@/types/api';

export function fetchDataFiles() {
  return httpGet<{ files: DataFileItem[] }>('/api/data/files');
}
