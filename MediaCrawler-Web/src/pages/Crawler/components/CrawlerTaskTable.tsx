import {
  Button,
  Select,
  Space,
  Table,
  Tag,
} from 'antd';
import { ReloadOutlined, DeleteOutlined, StopOutlined, CaretRightOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useQuery } from '@tanstack/react-query';

import { calcDuration } from '@/utils/format';
import {
  PLATFORM_LABELS,
  CRAWLER_TYPE_LABELS,
  TASK_STATUS_CONFIG,
} from '@/constants';
import { fetchEnabledPlatforms } from '@/api/modules/platforms';
import type { CrawlerTask } from '@/types/config';

interface Props {
  dataSource: CrawlerTask[];
  loading: boolean;
  fetching: boolean;
  statusFilter: string | undefined;
  platformFilter: string | undefined;
  page: number;
  total: number;
  pageSize: number;
  rerunPending: boolean;
  executePending: boolean;
  onStatusChange: (v: string | undefined) => void;
  onPlatformChange: (v: string | undefined) => void;
  onPageChange: (p: number) => void;
  onRowClick: (task: CrawlerTask) => void;
  onRerun: (taskId: number) => void;
  onDelete: (taskId: number) => void;
  onExecute: (taskId: number) => void;
  onRefresh: () => void;
  onStop?: (taskId: number) => void;
  stopPending?: boolean;
}

export default function CrawlerTaskTable({
  dataSource,
  loading,
  fetching,
  statusFilter,
  platformFilter,
  page,
  total,
  pageSize,
  rerunPending,
  executePending,
  onStatusChange,
  onPlatformChange,
  onPageChange,
  onRowClick,
  onRerun,
  onDelete,
  onExecute,
  onRefresh,
  onStop,
  stopPending,
}: Props) {
  const { data: platforms } = useQuery({
    queryKey: ['platforms', 'enabled'],
    queryFn: fetchEnabledPlatforms,
    staleTime: 5 * 60 * 1000,
  });

  const getPlatformName = (code: string) =>
    platforms?.find((p) => p.code === code)?.name || PLATFORM_LABELS[code] || code || '—';

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    {
      title: '平台',
      key: 'platform',
      width: 80,
      render: (_: unknown, r: CrawlerTask) =>
        getPlatformName(r.payload_snapshot?.platform || ''),
    },
    {
      title: '类型',
      key: 'crawler_type',
      width: 80,
      render: (_: unknown, r: CrawlerTask) =>
        CRAWLER_TYPE_LABELS[r.payload_snapshot?.crawler_type] ||
        r.payload_snapshot?.crawler_type ||
        '—',
    },
    {
      title: '关键词',
      key: 'keywords',
      ellipsis: true,
      render: (_: unknown, r: CrawlerTask) =>
        r.payload_snapshot?.keywords || r.payload_snapshot?.specified_ids || r.payload_snapshot?.creator_ids || '—',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s: string) => {
        const cfg = TASK_STATUS_CONFIG[s] || { color: 'default', label: s };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (v: string) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm:ss') : '—'),
    },
    {
      title: '耗时',
      key: 'duration',
      width: 100,
      render: (_: unknown, r: CrawlerTask) => calcDuration(r),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: unknown, r: CrawlerTask) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              onRowClick(r);
            }}
          >
            详情
          </Button>
          {r.status === 'running' && onStop && (
            <Button
              type="link"
              danger
              size="small"
              icon={<StopOutlined />}
              loading={stopPending}
              onClick={(e) => {
                e.stopPropagation();
                onStop(r.id);
              }}
            >
              停止
            </Button>
          )}
          {(r.status === 'pending' || r.status === 'cancelled') && (
            <Button
              type="link"
              size="small"
              icon={<CaretRightOutlined />}
              loading={executePending}
              onClick={(e) => {
                e.stopPropagation();
                onExecute(r.id);
              }}
            >
              执行
            </Button>
          )}
          {r.status === 'failed' && (
            <Button
              type="link"
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onRerun(r.id);
              }}
              loading={rerunPending}
            >
              重跑
            </Button>
          )}
          {(r.status === 'completed' || r.status === 'failed') && (
            <Button
              type="link"
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onDelete(r.id);
              }}
            />
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          allowClear
          placeholder="平台筛选"
          style={{ minWidth: 120 }}
          value={platformFilter}
          onChange={(val) => {
            onPlatformChange(val);
            onPageChange(1);
          }}
          options={(platforms ?? []).map((p) => ({ value: p.code, label: p.name }))}
        />
        <Select
          allowClear
          placeholder="状态过滤"
          style={{ minWidth: 120 }}
          value={statusFilter}
          onChange={(val) => {
            onStatusChange(val);
            onPageChange(1);
          }}
          options={Object.entries(TASK_STATUS_CONFIG).map(([value, cfg]) => ({
            value,
            label: cfg.label,
          }))}
        />
        <Button
          icon={<ReloadOutlined />}
          loading={fetching}
          onClick={onRefresh}
        >
          刷新
        </Button>
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        rowClassName={(_: unknown, r: CrawlerTask) => {
          if (r.status === 'failed') return 'row-failed';
          if (r.status === 'running') return 'row-running';
          return '';
        }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: false,
          showTotal: (t) => `共 ${t} 条`,
          onChange: onPageChange,
        }}
        locale={{ emptyText: '暂无任务记录，请先启动爬虫' }}
        onRow={(r) => ({
          onClick: () => onRowClick(r),
          style: { cursor: 'pointer' },
        })}
      />
    </>
  );
}
