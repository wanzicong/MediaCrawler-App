import { httpGet, httpPost } from '../request';
import request from '../request';

export interface BookmarkInfo {
  is_bookmarked: boolean;
  review_status: string | null;
}

export interface BatchCheckResult {
  items: Record<string, BookmarkInfo>;
}

export interface BookmarkListItem {
  content_id: string;
  review_status: string | null;
  created_at: string;
  updated_at: string;
}

export interface BookmarkListResult {
  platform: string;
  items: BookmarkListItem[];
  total: number;
  page: number;
  page_size: number;
}

export function toggleBookmark(platform: string, content_id: string) {
  return httpPost<{ is_bookmarked: boolean; action: string }>('/api/bookmarks/toggle', { platform, content_id });
}

export function updateReviewStatus(platform: string, content_id: string, review_status: string | null) {
  return request.put<{ ok: boolean }>('/api/bookmarks/status', { platform, content_id, review_status });
}

export function checkBookmark(platform: string, content_id: string) {
  return httpGet<BookmarkInfo>(`/api/bookmarks/check?platform=${platform}&content_id=${encodeURIComponent(content_id)}`);
}

export function batchCheckBookmarks(platform: string, content_ids: string[]) {
  return httpPost<BatchCheckResult>('/api/bookmarks/batch-check', { platform, content_ids });
}

export function listBookmarks(platform: string, page = 1, page_size = 20) {
  return httpGet<BookmarkListResult>(`/api/bookmarks/list?platform=${platform}&page=${page}&page_size=${page_size}`);
}
