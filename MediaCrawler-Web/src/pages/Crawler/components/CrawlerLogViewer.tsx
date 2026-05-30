import { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Card, Space, Tag, Typography, theme } from 'antd';
import {
  ClearOutlined,
  ColumnHeightOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
  ReloadOutlined,
  WifiOutlined,
} from '@ant-design/icons';
import type { CrawlerLogEntry } from '@/api/modules/crawler';

interface Props {
  logs: CrawlerLogEntry[];
  connected: boolean;
  onClear: () => void;
  onRefresh: () => void;
}

const LEVEL_CONFIG: Record<string, { color: string; label: string }> = {
  info: { color: 'default', label: 'INFO' },
  warning: { color: 'warning', label: 'WARN' },
  error: { color: 'error', label: 'ERROR' },
  success: { color: 'success', label: 'OK' },
  debug: { color: 'processing', label: 'DEBUG' },
};

const MIN_LOG_HEIGHT = 180;
const MAX_LOG_HEIGHT = typeof window !== 'undefined' ? window.innerHeight - 120 : 800;
const DEFAULT_LOG_HEIGHT = 320;

export default function CrawlerLogViewer({ logs, connected, onClear, onRefresh }: Props) {
  const { token } = theme.useToken();
  const containerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [logHeight, setLogHeight] = useState(DEFAULT_LOG_HEIGHT);
  const [isResizing, setIsResizing] = useState(false);
  const resizeStartY = useRef(0);
  const resizeStartH = useRef(DEFAULT_LOG_HEIGHT);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScrollRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  // ESC key to exit fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreen]);

  // 拖拽调整日志窗口高度
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    resizeStartY.current = e.clientY;
    resizeStartH.current = logHeight;
  }, [logHeight]);

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e: MouseEvent) => {
      const delta = resizeStartY.current - e.clientY;
      const newHeight = Math.min(MAX_LOG_HEIGHT, Math.max(MIN_LOG_HEIGHT, resizeStartH.current + delta));
      setLogHeight(newHeight);
    };
    const handleMouseUp = () => setIsResizing(false);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    autoScrollRef.current = scrollHeight - scrollTop - clientHeight < 40;
  };

  const cardStyle = isFullscreen ? {
    position: 'fixed' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 1050,
    margin: 0,
    borderRadius: 0,
  } : {};

  const logPanelHeight = isFullscreen ? 'calc(100vh - 58px)' : logHeight;

  return (
    <Card
      size="small"
      title={
        <Space size={8}>
          <span>运行日志</span>
          <Tag
            color={connected ? 'success' : 'default'}
            icon={<WifiOutlined />}
            style={{ fontSize: 11, lineHeight: '18px' }}
          >
            {connected ? '实时' : '离线'}
          </Tag>
        </Space>
      }
      extra={
        <Space size={4}>
          {!isFullscreen && (
            <Button
              type="text"
              size="small"
              icon={<ColumnHeightOutlined />}
              onClick={() => setLogHeight(logHeight < 500 ? 600 : DEFAULT_LOG_HEIGHT)}
              title="切换日志窗口高度"
            />
          )}
          <Button
            type="text"
            size="small"
            icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? '退出全屏 (Esc)' : '全屏'}
          />
          <Button
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            onClick={onRefresh}
          />
          <Button
            type="text"
            size="small"
            icon={<ClearOutlined />}
            onClick={onClear}
          />
        </Space>
      }
      styles={{ body: { padding: 0 } }}
      style={cardStyle}
    >
      {/* 拖拽手柄（非全屏时显示） */}
      {!isFullscreen && (
        <div
          onMouseDown={handleResizeStart}
          style={{
            height: 6,
            cursor: 'ns-resize',
            background: isResizing ? token.colorPrimary : '#1E293B',
            borderTop: '1px solid #334155',
            transition: isResizing ? 'none' : 'background 0.15s',
            userSelect: 'none',
          }}
          title="拖拽调整日志窗口高度"
        />
      )}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          height: logPanelHeight,
          overflow: 'auto',
          background: '#0F172A',
          fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace",
          fontSize: 12,
          lineHeight: '20px',
          padding: '8px 0',
        }}
      >
        {logs.length === 0 ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: token.colorTextDisabled,
            }}
          >
            <Typography.Text type="secondary" style={{ color: '#64748B' }}>
              暂无日志，启动爬虫后此处将实时显示运行输出
            </Typography.Text>
          </div>
        ) : (
          logs.map((entry) => {
            const cfg = LEVEL_CONFIG[entry.level] || LEVEL_CONFIG.info;
            return (
              <div
                key={entry.id}
                style={{
                  padding: '1px 12px',
                  display: 'flex',
                  gap: 8,
                  alignItems: 'flex-start',
                }}
              >
                <span style={{ color: '#475569', flexShrink: 0, width: 62, textAlign: 'right' }}>
                  {entry.timestamp}
                </span>
                <Tag
                  color={cfg.color}
                  style={{ fontSize: 10, lineHeight: '16px', margin: '2px 0', flexShrink: 0, minWidth: 38, textAlign: 'center' }}
                >
                  {cfg.label}
                </Tag>
                <span
                  style={{
                    color: entry.level === 'error' ? '#FCA5A5' : entry.level === 'warning' ? '#FDE68A' : '#E2E8F0',
                    wordBreak: 'break-all',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {entry.message}
                </span>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
