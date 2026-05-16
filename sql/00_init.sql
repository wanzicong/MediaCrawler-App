-- MediaCrawler MySQL 初始化（Docker 首次启动时执行）
-- 账号：root / 123456（由 docker-compose 环境变量设置）

CREATE DATABASE IF NOT EXISTS `media_crawler`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `media_crawler`;

SET NAMES utf8mb4;
