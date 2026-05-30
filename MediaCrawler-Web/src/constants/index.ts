/** 应用名称 */
export const APP_TITLE = 'MediaCrawler 控制台';

/** 本地存储键 */
export const STORAGE_KEYS = {
  SIDEBAR_COLLAPSED: 'mediacrawler_sidebar_collapsed',
} as const;

export {
  PLATFORM_LABELS,
  CRAWLER_TYPE_LABELS,
  KIND_LABELS,
  CONTENT_ID_FIELDS,
  ZHIHU_CONTENT_TYPE_LABELS,
  PLATFORM_URL_FIELDS,
  getPlatformUrl,
} from './platforms';

export {
  TASK_STATUS_CONFIG,
  CRAWLER_STATUS_LABELS,
} from './status';

export {
  IMPORTANT_FIELDS,
  FIELD_LABELS,
  TS_FIELDS,
  IMAGE_FIELDS,
} from './fields';
