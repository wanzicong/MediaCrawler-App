import dayjs from 'dayjs';
import type { CrawlerTask } from '@/types/config';
import { TS_FIELDS } from '@/constants/fields';

export function isImageUrl(s: string): boolean {
  return s.startsWith('http://') || s.startsWith('https://') || s.startsWith('//');
}

/** 将 HTTP 图片链接升级为 HTTPS，避免浏览器阻止混合内容或 CDN 防盗链 */
export function normalizeImageUrl(url: string): string {
  if (url.startsWith('http://')) {
    return url.replace('http://', 'https://');
  }
  if (url.startsWith('//')) {
    return `https:${url}`;
  }
  return url;
}

export function formatText(key: string, v: unknown): string {
  if (v == null) return '—';
  if (typeof v === 'string' && TS_FIELDS.has(key)) {
    const num = Number(v);
    if (!Number.isNaN(num)) {
      const sec = num > 1e12 ? num / 1000 : num;
      return dayjs.unix(sec).format('YYYY-MM-DD HH:mm:ss');
    }
  }
  if (typeof v === 'number' && TS_FIELDS.has(key)) {
    const sec = v > 1e12 ? v / 1000 : v;
    return dayjs.unix(sec).format('YYYY-MM-DD HH:mm:ss');
  }
  const s = String(v);
  return s.length > 80 ? `${s.slice(0, 80)}…` : s;
}

export function calcDuration(task: CrawlerTask): string {
  if (!task.started_at) return '—';
  const start = dayjs.utc(task.started_at);
  const end = task.finished_at
    ? dayjs.utc(task.finished_at)
    : task.status === 'running'
      ? dayjs.utc()
      : null;
  if (!end) return '进行中';
  const sec = end.diff(start, 'second');
  if (sec < 60) return `${sec}秒`;
  if (sec < 3600) return `${Math.floor(sec / 60)}分${sec % 60}秒`;
  return `${Math.floor(sec / 3600)}时${Math.floor((sec % 3600) / 60)}分`;
}

/** Convert hex color to rgba string with given alpha */
export function colorToRgba(hex: string, alpha: number): string {
  const clean = hex.replace('#', '');
  if (clean.length !== 6) return hex;
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
