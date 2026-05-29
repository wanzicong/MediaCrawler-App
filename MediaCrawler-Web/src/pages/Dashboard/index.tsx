import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App, Card, Col, Row, Typography, theme } from 'antd';

import { fetchEnvCheck, fetchHealth, fetchCrawlerTasks, stopCrawler } from '@/api';
import { fetchDatabaseStatus, initDatabase } from '@/api/modules/system';
import PageHeader from '@/components/PageHeader';
import { useCrawlerStatus } from '@/hooks/useCrawlerStatus';

import DashboardMetricCards from './components/DashboardMetricCards';
import DashboardRecentTasks from './components/DashboardRecentTasks';
import DashboardQuickActions from './components/DashboardQuickActions';

export default function DashboardPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const { token } = theme.useToken();

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

  const { data: recentTasks, isLoading: recentTasksLoading } = useQuery({
    queryKey: ['crawler-tasks', 1, undefined],
    queryFn: () => fetchCrawlerTasks({ page: 1, page_size: 5 }),
    refetchInterval: 15000,
  });

  const initDbMutation = useMutation({
    mutationFn: initDatabase,
    onSuccess: (res) => {
      message.success(res.message || '数据库初始化成功');
      void refetchDb();
      void queryClient.invalidateQueries({ queryKey: ['profiles'] });
    },
  });

  const stopMutation = useMutation({
    mutationFn: stopCrawler,
    onSuccess: () => {
      message.success('已发送停止指令');
      void queryClient.invalidateQueries({ queryKey: ['crawler', 'status'] });
    },
  });

  return (
    <>
      <PageHeader
        title="概览"
        description="系统运行状态与快速入口"
      />

      <DashboardMetricCards
        health={health}
        healthLoading={healthLoading}
        dbStatus={dbStatus}
        dbLoading={dbLoading}
        refetchDb={refetchDb}
        envCheck={envCheck}
        envLoading={envLoading}
        crawlerStatus={crawlerStatus}
        statusLoading={statusLoading}
        initDbMutation={initDbMutation}
        token={token}
        onStopCrawler={() => stopMutation.mutate()}
        stopPending={stopMutation.isPending}
      />

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={14}>
          <DashboardRecentTasks
            tasks={recentTasks?.items ?? []}
            loading={recentTasksLoading}
          />
        </Col>
        <Col xs={24} lg={10}>
          <DashboardQuickActions />
        </Col>
      </Row>

      {dbStatus && !dbStatus.connected && dbStatus.error && (
        <Card title="MySQL 连接异常" style={{ marginTop: 16 }}>
          <Typography.Text type="danger">{dbStatus.error}</Typography.Text>
          <br />
          <Typography.Text type="secondary">
            请在 MediaCrawler-Api 目录配置 .env（参考 .env.example）并启动 MySQL 服务。
          </Typography.Text>
        </Card>
      )}

      {envCheck && !envCheck.success && envCheck.error && (
        <Card title="环境检查详情" style={{ marginTop: 16 }}>
          <Typography.Text type="danger" copyable>
            {envCheck.error}
          </Typography.Text>
        </Card>
      )}
    </>
  );
}
