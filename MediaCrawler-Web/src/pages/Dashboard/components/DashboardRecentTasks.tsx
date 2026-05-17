import { Card, Table, Tag, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { PLATFORM_LABELS, TASK_STATUS_CONFIG } from '@/constants';
import type { CrawlerTask } from '@/types/config';

interface Props {
  tasks: CrawlerTask[];
  loading: boolean;
}

export default function DashboardRecentTasks({ tasks, loading }: Props) {
  const navigate = useNavigate();

  return (
    <Card
      title="最近任务"
      size="small"
      extra={
        <Typography.Link onClick={() => navigate('/crawler')}>
          查看全部
        </Typography.Link>
      }
    >
     <Table<CrawlerTask>
       dataSource={tasks}
       rowKey="id"
       loading={loading}
       pagination={false}
       size="small"
        bordered={false}
        showHeader={true}
       columns={[
          { title: 'ID', dataIndex: 'id', width: 50 },
          {
            title: '平台',
            width: 80,
            render: (_: unknown, r: CrawlerTask) =>
              PLATFORM_LABELS[r.payload_snapshot?.platform] || r.payload_snapshot?.platform || '—',
          },
          {
            title: '关键词',
            ellipsis: true,
            render: (_: unknown, r: CrawlerTask) =>
              r.payload_snapshot?.keywords || r.payload_snapshot?.specified_ids || '—',
          },
          {
            title: '状态',
            width: 80,
            render: (_: unknown, r: CrawlerTask) => {
              const cfg = TASK_STATUS_CONFIG[r.status] || { color: 'default', label: r.status };
              return <Tag color={cfg.color}>{cfg.label}</Tag>;
            },
          },
        ]}
        locale={{ emptyText: '暂无任务记录' }}
      />
    </Card>
  );
}
