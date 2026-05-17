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
