// NOTE: 平台数据已迁移到数据库，通过 GET /api/platforms 获取
// 以下常量仅作为 fallback，新代码应使用 fetchEnabledPlatforms()
export const PLATFORM_LABELS: Record<string, string> = {
  xhs: '小红书',
  dy: '抖音',
  ks: '快手',
  bili: 'B站',
  wb: '微博',
  tieba: '贴吧',
  zhihu: '知乎',
};

export const CRAWLER_TYPE_LABELS: Record<string, string> = {
  search: '搜索',
  detail: '详情',
  creator: '创作者',
};

export const KIND_LABELS: Record<string, string> = {
  contents: '内容',
  comments: '评论',
  creators: '创作者',
};

export const CONTENT_ID_FIELDS: Record<string, string> = {
  xhs: 'note_id',
  dy: 'aweme_id',
  ks: 'video_id',
  bili: 'video_id',
  wb: 'note_id',
  tieba: 'note_id',
  zhihu: 'content_id',
};

/** 知乎内容类型标签 */
export const ZHIHU_CONTENT_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  answer: { label: '答案', color: 'blue' },
  article: { label: '文章', color: 'green' },
  zvideo: { label: '视频', color: 'orange' },
};

/** 各平台数据中存储原始链接的字段名（数据库已存完整URL） */
export const PLATFORM_URL_FIELDS: Record<string, string[]> = {
  xhs: ['note_url'],
  dy: ['aweme_url'],
  ks: ['video_url'],
  bili: ['video_url'],
  wb: ['note_url'],
  tieba: ['note_url'],
  zhihu: ['content_url'],
};

/** 从数据行中提取原始平台链接 */
export function getPlatformUrl(platform: string, row: Record<string, unknown>): string | null {
  const fields = PLATFORM_URL_FIELDS[platform];
  if (!fields) return null;
  for (const f of fields) {
    const v = row[f];
    if (v != null && typeof v === 'string' && v.startsWith('http')) return v;
  }
  return null;
}
