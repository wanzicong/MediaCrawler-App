/** 爬虫任务状态 (CrawlerTask.status) */
export const TASK_STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '排队中' },
  running: { color: 'processing', label: '运行中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
  cancelled: { color: 'warning', label: '已取消' },
};

/** 爬虫进程状态 (CrawlerManager.status) */
export const CRAWLER_STATUS_LABELS: Record<string, string> = {
  idle: '空闲',
  running: '运行中',
  stopping: '停止中',
  error: '异常',
};
