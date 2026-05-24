import { Empty, Result, Skeleton, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';

interface Props {
  columns: ColumnsType<Record<string, unknown>>;
  dataSource: Record<string, unknown>[];
  isLoading: boolean;
  isError: boolean;
  error?: Error | null;
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (p: number) => void;
  onPageSizeChange?: (size: number) => void;
  onRowClick: (row: Record<string, unknown>) => void;
}

export default function DataTable({
  columns,
  dataSource,
  isLoading,
  isError,
  error,
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  onRowClick,
}: Props) {
  if (isLoading) {
    return <Skeleton active paragraph={{ rows: 8 }} />;
  }

  if (isError) {
    return (
      <Result
        status="error"
        title="数据加载失败"
        subTitle={(error as Error)?.message || '未知错误'}
      />
    );
  }

  if (dataSource.length === 0) {
    return <Empty description="暂无数据，请先完成至少一次爬取任务" />;
  }

  return (
    <Table<Record<string, unknown>>
      className="data-table"
     rowKey={(r, idx) => String(r.id ?? r.note_id ?? r.comment_id ?? r.video_id ?? r.aweme_id ?? idx)}
      columns={columns}
      dataSource={dataSource}
      scroll={{ x: 'max-content' }}
      size="middle"
      pagination={{
        current: page,
        pageSize,
        total,
        showSizeChanger: true,
        pageSizeOptions: ['10', '20', '50', '100', '200'],
        showTotal: (t) => `共 ${t} 条`,
        onChange: onPageChange,
        onShowSizeChange: (_current, size) => {
          onPageSizeChange?.(size);
          onPageChange(1);
        },
      }}
      onRow={(r) => ({
        onClick: () => onRowClick(r),
        style: { cursor: 'pointer' },
      })}
    />
  );
}
