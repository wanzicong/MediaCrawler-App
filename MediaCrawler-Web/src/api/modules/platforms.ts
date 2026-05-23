import { httpGet } from '../request';
import request from '../request';

/** 平台信息（来自 GET /api/platforms） */
export interface PlatformInfo {
  id: number;
  code: string;
  name: string;
  icon: string;
  enabled: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

/** 获取全部平台列表 */
export function fetchAllPlatforms() {
  return httpGet<PlatformInfo[]>('/api/platforms');
}

/** 获取已启用的平台列表 */
export function fetchEnabledPlatforms() {
  return httpGet<PlatformInfo[]>('/api/platforms?enabled_only=true');
}

/** 更新单个平台信息 */
export function updatePlatform(id: number, data: Partial<Pick<PlatformInfo, 'name' | 'icon' | 'enabled'>>) {
  return request.put<PlatformInfo>(`/api/platforms/${id}`, data);
}

/** 批量更新平台排序 */
export function reorderPlatforms(order: number[]) {
  return request.put<{ status: string }>('/api/platforms/reorder', { order });
}
