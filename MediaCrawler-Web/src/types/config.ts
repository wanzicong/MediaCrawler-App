/** 配置方案 payload（与后端 CrawlerPayloadSchema 对齐） */
export interface CrawlerPayload {
  platform: string;
  login_type: string;
  crawler_type: string;
  keywords: string;
  specified_ids: string;
  creator_ids: string;
  start_page: number;
  enable_comments: boolean;
  enable_sub_comments: boolean;
  save_option: string;
  cookies: string;
  headless: boolean;
  enable_cdp_mode: boolean;
  cdp_headless: boolean;
  enable_ip_proxy: boolean;
  ip_proxy_pool_count: number;
  ip_proxy_provider_name: string;
  crawler_max_notes_count: number;
  max_concurrency_num: number;
  crawler_max_comments_count_singlenotes: number;
  crawler_max_sleep_sec: number;
  crawler_max_sleep_sec_max: number;
  enable_get_medias: boolean;
  enable_get_wordcloud: boolean;
  save_login_state: boolean;
  xhs_international: boolean;
}

export interface CrawlerProfile {
  id: number;
  name: string;
  description: string;
  is_default: boolean;
  payload: CrawlerPayload;
  created_at?: string;
  updated_at?: string;
}

export interface CrawlerTask {
  id: number;
  profile_id: number | null;
  status: string;
  payload_snapshot: CrawlerPayload;
  error_message?: string | null;
  progress?: {
    page?: number;
    keyword?: string;
    crawled?: number;
  } | null;
  created_at?: string;
  started_at?: string;
  finished_at?: string;
}

export interface TaskListResponse {
  items: CrawlerTask[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskRerunResponse {
  status: string;
  message: string;
  task_id: number;
  original_task_id: number;
}

export interface DbPlatformMeta {
  value: string;
  label: string;
  kinds: { value: string; label: string }[];
}

export interface DbQueryResult {
  platform: string;
  kind: string;
  items: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskDataStats {
  task_id: number;
  platforms: Record<string, {
    label: string;
    contents: number;
    comments: number;
  }>;
  total_contents: number;
  total_comments: number;
}

export const DEFAULT_PAYLOAD: CrawlerPayload = {
  platform: 'xhs',
  login_type: 'qrcode',
  crawler_type: 'search',
  keywords: '',
  specified_ids: '',
  creator_ids: '',
  start_page: 1,
  enable_comments: true,
  enable_sub_comments: false,
  save_option: 'db',
  cookies: '',
  headless: false,
  enable_cdp_mode: true,
  cdp_headless: false,
  enable_ip_proxy: false,
  ip_proxy_pool_count: 2,
  ip_proxy_provider_name: 'kuaidaili',
  crawler_max_notes_count: 100,
  max_concurrency_num: 2,
  crawler_max_comments_count_singlenotes: 30,
  crawler_max_sleep_sec: 5,
  crawler_max_sleep_sec_max: 15,
  enable_get_medias: false,
  enable_get_wordcloud: false,
  save_login_state: true,
  xhs_international: false,
};
