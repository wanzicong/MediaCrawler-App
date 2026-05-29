import { Button, Col, Row, Space, Tag, Typography } from 'antd';
import {
  ApiOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  RocketOutlined,
  StopOutlined,
} from '@ant-design/icons';
import type { GlobalToken } from 'antd/es/theme/interface';
import MetricCard from '@/components/MetricCard';
import { CRAWLER_STATUS_LABELS } from '@/constants';
import type { HealthResponse, EnvCheckResponse, CrawlerStatusResponse } from '@/types/api';

interface Props {
  health?: HealthResponse;
  healthLoading: boolean;
  dbStatus?: { connected: boolean; database?: string; host?: string; error?: string };
  dbLoading: boolean;
  refetchDb: () => void;
  envCheck?: EnvCheckResponse;
  envLoading: boolean;
  crawlerStatus?: CrawlerStatusResponse;
  statusLoading: boolean;
  initDbMutation: { isPending: boolean; mutate: () => void };
  token: GlobalToken;
  onStopCrawler?: () => void;
  stopPending?: boolean;
}

export default function DashboardMetricCards({
  health,
  healthLoading,
  dbStatus,
  dbLoading,
  refetchDb,
  envCheck,
  envLoading,
  crawlerStatus,
  statusLoading,
  initDbMutation,
  token,
  onStopCrawler,
  stopPending,
}: Props) {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} lg={6}>
        <MetricCard
          title='API 服务'
          value={health?.status === 'ok' ? '正常' : '异常'}
          icon={<CloudServerOutlined />}
          color={token.colorSuccess}
          loading={healthLoading}
          subtitle={health?.status === 'ok' ? '服务运行中' : undefined}
        />
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <MetricCard
          title='MySQL'
          value={dbStatus?.connected ? '已连接' : '未连接'}
          icon={<DatabaseOutlined />}
          color={token.colorPrimary}
          loading={dbLoading}
          subtitle={dbStatus?.database ? `${dbStatus.host} / ${dbStatus.database}` : undefined}
          extra={
            <Space>
              <Typography.Link onClick={() => initDbMutation.mutate()}>
                {initDbMutation.isPending ? '初始化中…' : '初始化库表'}
              </Typography.Link>
              <Typography.Link onClick={() => refetchDb()}>刷新</Typography.Link>
            </Space>
          }
        />
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <MetricCard
          title='爬虫环境'
          value={envCheck?.success ? '已就绪' : envLoading ? '检测中' : '未就绪'}
          icon={<ApiOutlined />}
          color={token.colorInfo}
          loading={envLoading}
        />
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <MetricCard
          title='爬虫状态'
          value={
            statusLoading
              ? '加载中'
              : CRAWLER_STATUS_LABELS[crawlerStatus?.status ?? 'idle'] ?? crawlerStatus?.status
          }
          icon={<RocketOutlined />}
          color={token.colorWarning}
          loading={statusLoading}
          extra={
            !statusLoading && (crawlerStatus?.task_id || crawlerStatus?.status === 'running') ? (
              <Space wrap>
                {crawlerStatus?.task_id && (
                  <Tag color='processing'>任务 #{crawlerStatus.task_id}</Tag>
                )}
                {(crawlerStatus?.status === 'running' || crawlerStatus?.status === 'stopping') && onStopCrawler && (
                  <Button
                    danger
                    size='small'
                    icon={<StopOutlined />}
                    loading={stopPending}
                    onClick={(e) => {
                      e.stopPropagation();
                      onStopCrawler();
                    }}
                  >
                    停止
                  </Button>
                )}
              </Space>
            ) : null
          }
        />
      </Col>
    </Row>
  );
}