-- 默认爬虫配置方案（与 Web「配置方案」一致）
USE `media_crawler`;

INSERT INTO `crawler_profile` (`name`, `description`, `is_default`, `payload`)
SELECT '默认方案', 'Docker SQL 初始化种子数据', 1, JSON_OBJECT(
  'platform', 'xhs',
  'login_type', 'qrcode',
  'crawler_type', 'search',
  'keywords', '编程副业,编程兼职',
  'specified_ids', '',
  'creator_ids', '',
  'start_page', 1,
  'enable_comments', true,
  'enable_sub_comments', false,
  'save_option', 'db',
  'cookies', '',
  'headless', false,
  'enable_cdp_mode', true,
  'cdp_headless', false,
  'enable_ip_proxy', false,
  'ip_proxy_pool_count', 2,
  'ip_proxy_provider_name', 'kuaidaili',
  'crawler_max_notes_count', 15,
  'max_concurrency_num', 1,
  'crawler_max_comments_count_singlenotes', 10,
  'crawler_max_sleep_sec', 2,
  'enable_get_medias', false,
  'enable_get_wordcloud', false,
  'save_login_state', true,
  'xhs_international', false
)
WHERE NOT EXISTS (SELECT 1 FROM `crawler_profile` WHERE `name` = '默认方案');
