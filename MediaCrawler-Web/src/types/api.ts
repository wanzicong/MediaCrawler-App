/** 与 MediaCrawler-Api FastAPI 对齐的类型定义 */

export type PlatformCode = 'xhs' | 'dy' | 'ks' | 'bili' | 'wb' | 'tieba' | 'zhihu';
export type LoginType = 'qrcode' | 'phone' | 'cookie';
export type CrawlerType = 'search' | 'detail' | 'creator';
export type SaveOption = 'jsonl' | 'json' | 'csv' | 'excel' | 'sqlite' | 'db' | 'mongodb';
export type CrawlerStatus = 'idle' | 'running' | 'stopping' | 'error';

export interface PlatformItem {
  value: PlatformCode;
  label: string;
  icon: string;
}

export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
}

export interface ConfigOptionsResponse {
  login_types: SelectOption<LoginType>[];
  crawler_types: SelectOption<CrawlerType>[];
  save_options: SelectOption<SaveOption>[];
}

export interface CrawlerStartPayload {
  profile_id?: number | null;
  platform: PlatformCode;
  login_type?: LoginType;
  crawler_type?: CrawlerType;
  keywords?: string;
  specified_ids?: string;
  creator_ids?: string;
  start_page?: number;
  enable_comments?: boolean;
  enable_sub_comments?: boolean;
  save_option?: SaveOption; // 固定 db，保留字段兼容
  cookies?: string;
  headless?: boolean;
}

export interface CrawlerStatusResponse {
  status: CrawlerStatus;
  platform?: string | null;
  crawler_type?: string | null;
  started_at?: string | null;
  message?: string | null;
  task_id?: number | null;
}

export interface ApiResponse<T = unknown> {
  status?: string;
  message?: string;
  data?: T;
}

export interface HealthResponse {
  status: string;
}

export interface EnvCheckResponse {
  success: boolean;
  message: string;
  output?: string;
  error?: string;
}

export interface DataFileItem {
  name: string;
  path: string;
  size: number;
  modified_at: number | string;
  record_count?: number | null;
}
