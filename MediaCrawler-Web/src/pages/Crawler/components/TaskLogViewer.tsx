import { useState, useEffect, useRef } from 'react';
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
} from 'antd';
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

export default function TaskLogViewer({ taskId, open, onClose }: Props) {
  const [selectedLevels, setSelectedLevels] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  // Build level filter param: only pass selected levels if some (not all) are selected
  const levelParam =
    selectedLevels.length > 0 && selectedLevels.length < ALL_LEVELS.length
      ? selectedLevels.join(',')
      : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ['task-logs', taskId, levelParam, page, pageSize],
    queryFn: () =>
      fetchTaskLogs(taskId!, {
        level: levelParam,
        page,
        page_size: pageSize,
      }),
    enabled: !!taskId && open,
    refetchInterval: open ? 5000 : false,
  });

  // Reset filters when modal opens with a new task
  useEffect(() => {
    if (open) {
      setSelectedLevels([]);
      setPage(1);
    }
  }, [open, taskId]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScrollRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [data?.logs]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    autoScrollRef.current = scrollHeight - scrollTop - clientHeight < 40;
  };

  const toggleLevel = (level: string) => {
    setSelectedLevels((prev) => {
      if (prev.includes(level)) {
        return prev.filter((l) => l !== level);
      }
      return [...prev, level];
    });
    setPage(1);
  };

  const formatTime = (recordedAt: string) => dayjs(recordedAt).format('HH:mm:ss');

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
      width={900}
      footer={null}
      destroyOnClose
    >
      {/* Level filter bar */}
      <Space wrap style={{ marginBottom: 12 }}>
        {ALL_LEVELS.map((level) => {
          const isSelected = selectedLevels.includes(level);
          const color = LEVEL_COLORS[level];
          return (
            <Tag
              key={level}
              color={isSelected ? color : undefined}
              style={{
                cursor: 'pointer',
                fontSize: 12,
                lineHeight: '20px',
                margin: 0,
                ...(isSelected
                  ? {}
                  : {
                      borderColor: color,
                      color,
                      backgroundColor: 'transparent',
                    }),
              }}
              onClick={() => toggleLevel(level)}
            >
              {LEVEL_LABELS[level]}
            </Tag>
          );
        })}
      </Space>

      {/* Log display area */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          height: 400,
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
        {isLoading ? (
          <div style={{ padding: 16 }}>
            <Skeleton active paragraph={{ rows: 8 }} />
          </div>
        ) : !data || data.logs.length === 0 ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
            }}
          >
            <Empty
              description={
                <Typography.Text style={{ color: '#64748B' }}>暂无日志记录</Typography.Text>
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </div>
        ) : (
          data.logs.map((entry) => {
            const color = LEVEL_COLORS[entry.level] || LEVEL_COLORS.info;
            const label = LEVEL_LABELS[entry.level] || entry.level.toUpperCase();
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
                <span
                  style={{
                    color: '#475569',
                    flexShrink: 0,
                    width: 62,
                    textAlign: 'right',
                  }}
                >
                  {formatTime(entry.recorded_at)}
                </span>
                <Tag
                  color={color}
                  style={{
                    fontSize: 10,
                    lineHeight: '16px',
                    margin: '2px 0',
                    flexShrink: 0,
                    minWidth: 38,
                    textAlign: 'center' as const,
                  }}
                >
                  {label}
                </Tag>
                <span
                  style={{
                    color,
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

      {/* Pagination */}
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
