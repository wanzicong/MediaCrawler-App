import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App, Button, Card, Col, Row, Space, Statistic, Tag, Typography } from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  LoadingOutlined,
} from '@ant-design/icons';

import { fetchEnvCheck, fetchHealth } from '@/api';
import { fetchDatabaseStatus, initDatabase } from '@/api/modules/system';
import PageHeader from '@/components/PageHeader';
import { useCrawlerStatus } from '@/hooks/useCrawlerStatus';

const statusColor: Record<string, string> = {
  idle: 'default',
  running: 'processing',
  stopping: 'warning',
  error: 'error',
};

const statusLabel: Record<string, string> = {
  idle: '空闲',
  running: '运行中',
  stopping: '停止中',
  error: '异常',
};

export default function DashboardPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  });

  const { data: envCheck, isLoading: envLoading } = useQuery({
    queryKey: ['env-check'],
    queryFn: fetchEnvCheck,
  });

  const { data: dbStatus, isLoading: dbLoading, refetch: refetchDb } = useQuery({
    queryKey: ['db-status'],
    queryFn: fetchDatabaseStatus,
    retry: false,
  });

  const { data: crawlerStatus, isLoading: statusLoading } = useCrawlerStatus(true);

  const initDbMutation = useMutation({
    mutationFn: initDatabase,
    onSuccess: (res) => {
      message.success(res.message || '数据库初始化成功');
      void refetchDb();
      void queryClient.invalidateQueries({ queryKey: ['profiles'] });
    },
  });

  return (
    <>
      <PageHeader
        title="概览"
        description="系统健康、MySQL 与爬虫运行状态；首次使用请先初始化数据库"
      />
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="API 服务"
              value={healthLoading ? '检测中' : health?.status === 'ok' ? '正常' : '异常'}
              prefix={
                healthLoading ? (
                  <LoadingOutlined />
                ) : health?.status === 'ok' ? (
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                ) : (
                  <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                )
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="MySQL"
              value={
                dbLoading ? '检测中' : dbStatus?.connected ? '已连接' : '未连接'
              }
              prefix={<DatabaseOutlined />}
            />
            {dbStatus?.database && (
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {dbStatus.host} / {dbStatus.database}
              </Typography.Text>
            )}
            <Space style={{ marginTop: 12 }}>
              <Button
                size="small"
                type="primary"
                loading={initDbMutation.isPending}
                onClick={() => initDbMutation.mutate()}
              >
                初始化库表
              </Button>
              <Button size="small" onClick={() => refetchDb()}>
                刷新
              </Button>
            </Space>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="爬虫环境"
              value={envLoading ? '检测中' : envCheck?.success ? '已就绪' : '未就绪'}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="爬虫状态"
              value={
                statusLoading
                  ? '加载中'
                  : statusLabel[crawlerStatus?.status ?? 'idle'] ?? crawlerStatus?.status
              }
            />
            {!statusLoading && crawlerStatus?.status && (
              <Space style={{ marginTop: 8 }}>
                <Tag color={statusColor[crawlerStatus.status]}>
                  {crawlerStatus.platform?.toUpperCase() || '—'}
                </Tag>
                {crawlerStatus.task_id && (
                  <Tag>任务 #{crawlerStatus.task_id}</Tag>
                )}
              </Space>
            )}
          </Card>
        </Col>
      </Row>
      {dbStatus && !dbStatus.connected && dbStatus.error && (
        <Card title="MySQL 连接" style={{ marginTop: 16 }}>
          <Typography.Paragraph type="danger">{dbStatus.error}</Typography.Paragraph>
          <Typography.Text type="secondary">
            请在 MediaCrawler-Api 目录配置 .env（参考 .env.example）并启动 MySQL 服务。
          </Typography.Text>
        </Card>
      )}
      {envCheck && !envCheck.success && envCheck.error && (
        <Card title="环境检查详情" style={{ marginTop: 16 }}>
          <Typography.Paragraph type="danger" copyable>
            {envCheck.error}
          </Typography.Paragraph>
        </Card>
      )}
    </>
  );
}
