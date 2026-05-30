import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Modal,
  Tag,
  Pagination,
  Skeleton,
  Space,
  Badge,
  Typography,
  Empty,
  Button,
} from 'antd';
import {
  ColumnHeightOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { fetchTaskLogs } from '@/api/modules/crawler';

interface Props {
  taskId: number | null;
  open: boolean;
  onClose: () => void;
}

const LEVEL_COLORS: Record<string, string> = {
  info: '#d4d4d4',
  warning: '#faad14',
  error: '#ff4d4f',
  success: '#52c41a',
  debug: '#8c8c8c',
};

const LEVEL_LABELS: Record<string, string> = {
  info: 'INFO',
  warning: 'WARN',
  error: 'ERROR',
  success: 'OK',
  debug: 'DEBUG',
};

const ALL_LEVELS = ['info', 'warning', 'error', 'success', 'debug'];
const MIN_LOG_H = 200;
const DEFAULT_LOG_H = 400;
const MAX_LOG_H = typeof window !== 'undefined' ? window.innerHeight - 200 : 800;

export default function TaskLogViewer({ taskId, open, onClose }: Props) {
  const [selectedLevels, setSelectedLevels] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);
  const [logHeight, setLogHeight] = useState(DEFAULT_LOG_H);
  const [isResizing, setIsResizing] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const resizeStartY = useRef(0);
  const resizeStartH = useRef(DEFAULT_LOG_H);

  const levelParam =
    selectedLevels.length > 0 && selectedLevels.length < ALL_LEVELS.length
      ? selectedLevels.join(',')
      : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ['task-logs', taskId, levelParam, page, pageSize],
    queryFn: () =>
      fetchTaskLogs(taskId!, { level: levelParam, page, page_size: pageSize }),
    enabled: !!taskId && open,
    refetchInterval: open ? 5000 : false,
  });

  useEffect(() => {
    if (open) {
      setSelectedLevels([]);
      setPage(1);
      setLogHeight(DEFAULT_LOG_H);
      setIsFullscreen(false);
    }
  }, [open, taskId]);

  useEffect(() => {
    if (autoScrollRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [data?.logs]);

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

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    autoScrollRef.current = scrollHeight - scrollTop - clientHeight < 40;
  };

  const toggleLevel = (level: string) => {
    setSelectedLevels((prev) => {
      if (prev.includes(level)) return prev.filter((l) => l !== level);
      return [...prev, level];
    });
    setPage(1);
  };

  const formatTime = (v: string) => {
    if (!v) return '--:--:--';
    // 兼容多种时间格式：ISO 8601、MySQL datetime、纯时间字符串
    const d = dayjs(v);
    if (d.isValid()) return d.format('HH:mm:ss');
    // 尝试提取 HH:MM:SS 部分
    const m = v.match(/(\d{2}:\d{2}:\d{2})/);
    return m ? m[1] : v.slice(0, 8);
  };

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    resizeStartY.current = e.clientY;
    resizeStartH.current = logHeight;
  }, [logHeight]);

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientY - resizeStartY.current;
      const newHeight = Math.min(MAX_LOG_H, Math.max(MIN_LOG_H, resizeStartH.current + delta));
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

  const modalStyle = isFullscreen ? {
    top: 0,
    maxWidth: '100vw',
    margin: 0,
    paddingBottom: 0,
  } : {};

  return (
    <Modal
      title={
        <Space size={8}>
          <span>任务日志</span>
          {taskId && <Tag style={{ fontSize: 12 }}>#{taskId}</Tag>}
          {data !== undefined && (
            <Badge count={data.total} showZero color="blue" overflowCount={99999} />
          )}
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={isFullscreen ? '100vw' : 900}
      footer={null}
      destroyOnClose
      style={modalStyle}
      styles={isFullscreen ? { body: { height: 'calc(100vh - 110px)', overflow: 'auto' } } : undefined}
    >
      <Space wrap style={{ marginBottom: 12, width: '100%', justifyContent: 'space-between' }}>
        <Space wrap>
          {ALL_LEVELS.map((level) => {
            const isSelected = selectedLevels.includes(level);
            const color = LEVEL_COLORS[level];
            return (
              <Tag
                key={level}
                color={isSelected ? color : undefined}
                style={{
                  cursor: 'pointer', fontSize: 12, lineHeight: '20px', margin: 0,
                  ...(isSelected ? {} : { borderColor: color, color, backgroundColor: 'transparent' }),
                }}
                onClick={() => toggleLevel(level)}
              >
                {LEVEL_LABELS[level]}
              </Tag>
            );
          })}
        </Space>
        <Space size={4}>
          <Button
            type="text"
            size="small"
            icon={<ColumnHeightOutlined />}
            onClick={() => setLogHeight(logHeight < 500 ? 600 : DEFAULT_LOG_H)}
            title="切换日志高度"
          />
          <Button
            type="text"
            size="small"
            icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? '退出全屏 (Esc)' : '全屏'}
          />
        </Space>
      </Space>

      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          height: isFullscreen ? 'calc(100vh - 190px)' : logHeight,
          overflow: 'auto',
          background: '#0F172A',
          fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace",
          fontSize: 12,
          lineHeight: '20px',
          padding: '8px 0',
          borderRadius: 6,
          marginBottom: 12,
        }}
      >
        {/* drag handle at bottom */}
        {!isFullscreen && (
          <div
            onMouseDown={handleResizeStart}
            style={{
              height: 5,
              cursor: 'ns-resize',
              background: isResizing ? '#1677ff' : '#1E293B',
              borderTop: '1px solid #334155',
              position: 'sticky',
              bottom: 0,
              userSelect: 'none',
            }}
            title="拖拽调整日志高度"
          />
        )}
        {isLoading ? (
          <div style={{ padding: 16 }}>
            <Skeleton active paragraph={{ rows: 8 }} />
          </div>
        ) : !data || data.logs.length === 0 ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <Empty
              description={<Typography.Text style={{ color: '#64748B' }}>暂无日志记录</Typography.Text>}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </div>
        ) : (
          data.logs.map((entry) => {
            const color = LEVEL_COLORS[entry.level] || LEVEL_COLORS.info;
            const label = LEVEL_LABELS[entry.level] || entry.level.toUpperCase();
            return (
              <div key={entry.id} style={{ padding: '1px 12px', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <span style={{ color: '#475569', flexShrink: 0, width: 62, textAlign: 'right' }}>
                  {formatTime(entry.recorded_at)}
                </span>
                <Tag color={color} style={{ fontSize: 10, lineHeight: '16px', margin: '2px 0', flexShrink: 0, minWidth: 38, textAlign: 'center' as const }}>
                  {label}
                </Tag>
                <span style={{ color, wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>{entry.message}</span>
              </div>
            );
          })
        )}
      </div>

      {data && data.total > 0 && (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <Pagination
            current={data.page}
            pageSize={data.page_size}
            total={data.total}
            onChange={(p) => setPage(p)}
            showSizeChanger={false}
            showTotal={(total) => `共 ${total} 条日志`}
            size="small"
          />
        </div>
      )}
    </Modal>
  );
}
