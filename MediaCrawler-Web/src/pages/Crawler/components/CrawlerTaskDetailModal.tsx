import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Modal,
  Row,
  Skeleton,
  Space,
  Tag,
  Typography,
  theme,
} from 'antd';
import { EyeOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import { calcDuration } from '@/utils/format';
import {
  PLATFORM_LABELS,
  CRAWLER_TYPE_LABELS,
  TASK_STATUS_CONFIG,
} from '@/constants';
import type { CrawlerTask, TaskDataStats } from '@/types/config';

interface Props {
  task: CrawlerTask | null;
  open: boolean;
  stats?: TaskDataStats;
  statsLoading: boolean;
  rerunPending: boolean;
  deletePending: boolean;
  onClose: () => void;
  onViewData: () => void;
  onRerun: () => void;
  onDelete: () => void;
}

export default function CrawlerTaskDetailModal({
  task,
  open,
  stats,
  statsLoading,
  rerunPending,
  deletePending,
  onClose,
  onViewData,
  onRerun,
  onDelete,
}: Props) {
  const { token } = theme.useToken();

  return (
    <Modal
      title={`任务 #${task?.id ?? ''}`}
      open={open}
      onCancel={onClose}
      width={720}
      footer={
        <Space>
          {task?.status === 'completed' && task?.payload_snapshot?.platform && (
            <Button icon={<EyeOutlined />} onClick={onViewData}>
              查看数据
            </Button>
          )}
          {task?.status === 'failed' && (
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              loading={rerunPending}
              onClick={onRerun}
            >
              重新执行
            </Button>
          )}
          {(task?.status === 'completed' || task?.status === 'failed' || task?.status === 'cancelled') && (
            <Button
              danger
              icon={<DeleteOutlined />}
              loading={deletePending}
              onClick={onDelete}
            >
              删除任务
            </Button>
          )}
          <Button onClick={onClose}>关闭</Button>
        </Space>
      }
    >
      {task && (
        <>
          <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="任务 ID">{task.id}</Descriptions.Item>
            <Descriptions.Item label="方案 ID">{task.profile_id ?? '—'}</Descriptions.Item>
            <Descriptions.Item label="平台">
              {PLATFORM_LABELS[task.payload_snapshot?.platform] || task.payload_snapshot?.platform}
            </Descriptions.Item>
            <Descriptions.Item label="爬取类型">
              {CRAWLER_TYPE_LABELS[task.payload_snapshot?.crawler_type] ||
                task.payload_snapshot?.crawler_type}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={TASK_STATUS_CONFIG[task.status]?.color}>
                {TASK_STATUS_CONFIG[task.status]?.label || task.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="耗时">{calcDuration(task)}</Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {task.created_at ? dayjs(task.created_at).format('YYYY-MM-DD HH:mm:ss') : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="开始时间">
              {task.started_at ? dayjs(task.started_at).format('YYYY-MM-DD HH:mm:ss') : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="结束时间" span={2}>
              {task.finished_at ? dayjs(task.finished_at).format('YYYY-MM-DD HH:mm:ss') : '—'}
            </Descriptions.Item>
            {task.error_message && (
              <Descriptions.Item label="错误信息" span={2}>
                {task.error_message}
              </Descriptions.Item>
            )}
          </Descriptions>

          {task.error_message && (
            <Alert
              type="error"
              showIcon
              message="任务失败原因"
              description={task.error_message}
              style={{ marginBottom: 16 }}
            />
          )}

          {task.progress && (task.progress.page != null || task.progress.keyword) && (
            <>
              <Typography.Title level={5}>爬取进度</Typography.Title>
              <Card size="small" style={{ marginBottom: 16 }}>
                {task.progress.keyword && (
                  <Descriptions size="small" column={2}>
                    <Descriptions.Item label="当前关键词">{task.progress.keyword}</Descriptions.Item>
                    <Descriptions.Item label="当前页">{task.progress.page ?? '—'}</Descriptions.Item>
                  </Descriptions>
                )}
                {!task.progress.keyword && task.progress.page != null && (
                  <Typography.Text type="secondary">
                    已爬取到第 {task.progress.page} 页
                  </Typography.Text>
                )}
              </Card>
            </>
          )}

          <Typography.Title level={5}>爬取数据统计</Typography.Title>
          {statsLoading ? (
            <Skeleton active paragraph={{ rows: 2 }} />
          ) : stats && stats.total_contents > 0 ? (
            <Card size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Typography.Text type="secondary">总内容数：</Typography.Text>
                  <Typography.Text strong>{stats.total_contents}</Typography.Text>
                </Col>
                <Col span={12}>
                  <Typography.Text type="secondary">总评论数：</Typography.Text>
                  <Typography.Text strong>{stats.total_comments}</Typography.Text>
                </Col>
                {Object.entries(stats.platforms).map(([key, p]) => (
                  <Col span={24} key={key}>
                    <Tag color="blue">{p.label}</Tag>
                    <Typography.Text type="secondary">
                      内容 {p.contents} 条 · 评论 {p.comments} 条
                    </Typography.Text>
                  </Col>
                ))}
              </Row>
            </Card>
          ) : (
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              暂无爬取数据
            </Typography.Text>
          )}

          <Typography.Title level={5}>配置快照</Typography.Title>
          <pre
            style={{
              maxHeight: 400,
              overflow: 'auto',
              background: token.colorFillAlter,
              border: `1px solid ${token.colorBorderSecondary}`,
              padding: 12,
              borderRadius: token.borderRadius,
              fontSize: 12,
              lineHeight: 1.5,
            }}
          >
            {JSON.stringify(task.payload_snapshot, null, 2)}
          </pre>
        </>
      )}
    </Modal>
  );
}
