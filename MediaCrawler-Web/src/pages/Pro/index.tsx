import { useState, useEffect } from 'react';
import {
  Card, Tabs, Table, Tag, Button, Space, InputNumber, Form,
  Select, Input, message, Descriptions, Popconfirm, Badge, Statistic,
  Row, Col, Typography, Spin, Empty,
} from 'antd';
import {
  ThunderboltOutlined, PauseCircleOutlined, PlayCircleOutlined,
  ReloadOutlined, DeleteOutlined, CheckCircleOutlined, SyncOutlined,
  ClockCircleOutlined, ApiOutlined, SearchOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import PageHeader from '@/components/PageHeader';
import { PLATFORM_LABELS } from '@/constants';
import { fetchEnabledPlatforms } from '@/api/modules/platforms';
import {
  fetchProStatus, fetchProConfig, startProCrawler, stopProCrawler,
  setMaxConcurrent, fetchCheckpoint, deleteCheckpoint,
  fetchAccounts, refreshAccounts,
} from '@/api/modules/pro';

const { Text } = Typography;

// ==================== 调度器状态面板 ====================
function SchedulerPanel() {
  const qc = useQueryClient();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['pro-status'],
    queryFn: fetchProStatus,
    refetchInterval: 3000,
  });

  const { data: config } = useQuery({
    queryKey: ['pro-config'],
    queryFn: fetchProConfig,
  });

  const { data: platforms } = useQuery({
    queryKey: ['platforms', 'enabled'],
    queryFn: fetchEnabledPlatforms,
    staleTime: 5 * 60 * 1000,
  });

  const platformOptions = (platforms ?? []).length > 0
    ? platforms!.map((p) => ({ label: p.name, value: p.code }))
    : Object.entries(PLATFORM_LABELS).map(([k, v]) => ({ label: v, value: k }));

  const [form] = Form.useForm();

  const startMut = useMutation({
    mutationFn: startProCrawler,
    onSuccess: (res) => message.success(`任务已提交 #${res.task_id}`),
    onError: (e: any) => message.error(e?.message || '启动失败'),
  });

  const maxMut = useMutation({
    mutationFn: setMaxConcurrent,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['pro-status'] }); message.success('并发数已更新'); },
  });

  const stopMut = useMutation({
    mutationFn: stopProCrawler,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['pro-status'] }); message.success('任务已停止'); },
  });

  const runningCols = [
    { title: '任务ID', dataIndex: 'task_id', key: 'task_id', width: 80 },
    { title: '平台', dataIndex: 'platform', key: 'platform', render: (v: string) => <Tag>{v}</Tag> },
    { title: '操作', key: 'act', width: 80, render: (_: any, r: any) => (
      <Popconfirm title="确定停止此任务?" onConfirm={() => stopMut.mutate(r.task_id)}>
        <Button size="small" danger icon={<PauseCircleOutlined />}>停止</Button>
      </Popconfirm>
    )},
  ];

  const waitingCols = [
    { title: '任务ID', dataIndex: 'task_id', key: 'task_id', width: 80 },
    { title: '平台', dataIndex: 'platform', key: 'platform', render: (v: string) => <Tag>{v}</Tag> },
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80,
      render: (v: number) => {
        const map: Record<number, { color: string; text: string }> = {
          0: { color: 'default', text: '低' },
          5: { color: 'blue', text: '普通' },
          10: { color: 'orange', text: '高' },
          20: { color: 'red', text: '紧急' },
        };
        const cfg = map[v] || map[5];
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
  ];

  return (
    <Spin spinning={isLoading}>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}><Card><Statistic title="最大并发" value={config?.max_concurrent ?? 3} prefix={<ApiOutlined />} /></Card></Col>
        <Col xs={12} sm={6}><Card><Statistic title="运行中" value={data?.running_count ?? 0} valueStyle={{ color: '#3f8600' }} prefix={<SyncOutlined spin={!!data?.running_count} />} /></Card></Col>
        <Col xs={12} sm={6}><Card><Statistic title="等待中" value={data?.waiting_count ?? 0} prefix={<ClockCircleOutlined />} /></Card></Col>
        <Col xs={12} sm={6}><Card><Statistic title="平台数" value={Object.keys(data?.platform_running ?? {}).length} prefix={<ThunderboltOutlined />} /></Card></Col>
      </Row>

      <Card title="提交新任务" size="small" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={(v) => startMut.mutate(v)}>
          <Form.Item name="platform" rules={[{ required: true }]}>
            <Select style={{ width: 100 }} placeholder="平台" options={platformOptions} />
          </Form.Item>
          <Form.Item name="crawler_type" rules={[{ required: true }]}>
            <Select style={{ width: 100 }} placeholder="类型"
              options={['search','detail','creator'].map(t => ({ label: t, value: t }))} />
          </Form.Item>
          <Form.Item name="keywords" rules={[{ required: true }]}>
            <Input placeholder="关键词 (逗号分隔)" style={{ width: 200 }} />
          </Form.Item>
          <Form.Item name="priority">
            <Select style={{ width: 90 }} placeholder="优先级" defaultValue="normal"
              options={[
                { label: '低', value: 'low' }, { label: '普通', value: 'normal' },
                { label: '高', value: 'high' }, { label: '紧急', value: 'urgent' },
              ]} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<PlayCircleOutlined />} loading={startMut.isPending}>
              提交任务
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Row gutter={16}>
        <Col xs={24} lg={12}>
          <Card title={`运行中 (${data?.running_count ?? 0})`} size="small" extra={
            <Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()}>刷新</Button>
          }>
            {data?.running?.length ? (
              <Table dataSource={data.running} columns={runningCols} rowKey="task_id" size="small" pagination={false} />
            ) : <Empty description="无运行中任务" />}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={`等待队列 (${data?.waiting_count ?? 0})`} size="small">
            {data?.waiting?.length ? (
              <Table dataSource={data.waiting} columns={waitingCols} rowKey="task_id" size="small" pagination={false} />
            ) : <Empty description="无等待任务" />}
          </Card>
        </Col>
      </Row>

      <Card title="并发控制" size="small" style={{ marginTop: 16 }}>
        <Space>
          <Text>最大并发数:</Text>
          <InputNumber min={1} max={10} defaultValue={config?.max_concurrent ?? 3}
            onChange={(v) => v && maxMut.mutate(v)} />
        </Space>
      </Card>
    </Spin>
  );
}

// ==================== 断点续爬面板 ====================
function CheckpointPanel() {
  const [taskId, setTaskId] = useState('');
  const [queryId, setQueryId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['checkpoint', queryId],
    queryFn: () => fetchCheckpoint(queryId!),
    enabled: queryId !== null,
  });

  const delMut = useMutation({
    mutationFn: deleteCheckpoint,
    onSuccess: () => message.success('断点已删除'),
  });

  return (
    <>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Input placeholder="输入任务 ID" value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            style={{ width: 150 }}
            onPressEnter={() => setQueryId(Number(taskId) || null)} />
          <Button type="primary" icon={<SearchOutlined />}
            onClick={() => setQueryId(Number(taskId) || null)}>查询断点</Button>
        </Space>
      </Card>

      {queryId !== null && (
        <Spin spinning={isLoading}>
          {data?.checkpoint ? (
            <Card title={`任务 #${queryId} 断点数据`} size="small" extra={
              <Popconfirm title="确定删除此断点?" onConfirm={() => delMut.mutate(queryId)}>
                <Button size="small" danger icon={<DeleteOutlined />}>删除断点</Button>
              </Popconfirm>
            }>
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="平台">{data.checkpoint.platform}</Descriptions.Item>
                <Descriptions.Item label="爬取类型">{data.checkpoint.crawler_type}</Descriptions.Item>
                <Descriptions.Item label="当前页">{data.checkpoint.current_page}</Descriptions.Item>
                <Descriptions.Item label="已爬取数">{data.checkpoint.total_crawled}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Badge status={data.checkpoint.status === 'running' ? 'processing' : 'success'}
                    text={data.checkpoint.status} />
                </Descriptions.Item>
                <Descriptions.Item label="关键词">{data.checkpoint.keywords || '-'}</Descriptions.Item>
              </Descriptions>
            </Card>
          ) : (
            <Empty description={`任务 #${queryId} 无断点数据`} />
          )}
        </Spin>
      )}
    </>
  );
}

// ==================== 多账号面板 ====================
function AccountPanel() {
  const qc = useQueryClient();

  const { data: platforms } = useQuery({
    queryKey: ['platforms', 'enabled'],
    queryFn: fetchEnabledPlatforms,
    staleTime: 5 * 60 * 1000,
  });

  const platformOptions = (platforms ?? []).length > 0
    ? platforms!.map((p) => ({ label: p.name, value: p.code }))
    : Object.entries(PLATFORM_LABELS).map(([k, v]) => ({ label: v, value: k }));

  const [platform, setPlatform] = useState(platformOptions[0]?.value ?? 'xhs');

  useEffect(() => {
    if (platforms && platforms.length > 0) {
      const codes = platforms.map((p) => p.code);
      if (!codes.includes(platform)) {
        setPlatform(platforms[0].code);
      }
    }
  }, [platforms]); // eslint-disable-line react-hooks/exhaustive-deps

  const { data, isLoading } = useQuery({
    queryKey: ['pro-accounts', platform],
    queryFn: () => fetchAccounts(platform),
  });

  const refreshMut = useMutation({
    mutationFn: () => refreshAccounts(platform),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['pro-accounts', platform] }); message.success('账号已刷新'); },
  });

  const cols = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '平台', dataIndex: 'platform', key: 'platform', render: (v: string) => <Tag>{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const map: Record<string, { color: string; text: string }> = {
        active: { color: 'green', text: '正常' },
        cooling: { color: 'orange', text: '冷却中' },
        rate_limited: { color: 'red', text: '限流' },
        banned: { color: '#999', text: '封禁' },
      };
      const cfg = map[v] || { color: 'default', text: v };
      return <Badge color={cfg.color} text={cfg.text} />;
    }},
    { title: '今日请求', dataIndex: 'daily_requests', key: 'daily_requests', width: 90 },
  ];

  return (
    <Spin spinning={isLoading}>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Text>平台:</Text>
          <Select value={platform} onChange={setPlatform} style={{ width: 100 }}
            options={platformOptions} />
          <Button icon={<ReloadOutlined />} onClick={() => refreshMut.mutate()} loading={refreshMut.isPending}>
            刷新账号
          </Button>
        </Space>
      </Card>

      <Card title={`${platform} 账号列表`} size="small" extra={
        <Text type="secondary">共 {data?.total_accounts ?? 0} 个 / 可用 {data?.available ?? 0} 个</Text>
      }>
        {data?.accounts?.length ? (
          <Table dataSource={data.accounts} columns={cols} rowKey="id" size="small" pagination={false} />
        ) : <Empty description={`暂无 ${platform} 账号`} />}
      </Card>
    </Spin>
  );
}

// ==================== Pro 主页面 ====================
export default function ProPage() {
  const tabItems = [
    {
      key: 'scheduler',
      label: <span><ThunderboltOutlined /> 任务调度</span>,
      children: <SchedulerPanel />,
    },
    {
      key: 'checkpoint',
      label: <span><CheckCircleOutlined /> 断点续爬</span>,
      children: <CheckpointPanel />,
    },
    {
      key: 'accounts',
      label: <span><ApiOutlined /> 多账号</span>,
      children: <AccountPanel />,
    },
  ];

  return (
    <>
      <PageHeader title="Pro 功能" desc="多任务并行 · 断点续爬 · 多账号管理 · 签名服务" />
      <Tabs defaultActiveKey="scheduler" items={tabItems} size="large" />
    </>
  );
}
