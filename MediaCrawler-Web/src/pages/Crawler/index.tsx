import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { PlayCircleOutlined, StopOutlined, ReloadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import dayjs from 'dayjs';

import {
  fetchConfigOptions,
  fetchPlatforms,
  startCrawler,
  stopCrawler,
  fetchCrawlerTasks,
  rerunCrawlerTask,
} from '@/api';
import { fetchProfiles } from '@/api/modules/configMgmt';
import PageHeader from '@/components/PageHeader';
import { useCrawlerStatus } from '@/hooks/useCrawlerStatus';
import type { CrawlerStartPayload, LoginType, PlatformCode } from '@/types/api';
import type { CrawlerTask } from '@/types/config';

const PLATFORM_LABELS: Record<string, string> = {
  xhs: '小红书',
  dy: '抖音',
  ks: '快手',
  bili: 'B站',
  wb: '微博',
  tieba: '贴吧',
  zhihu: '知乎',
};

const CRAWLER_TYPE_LABELS: Record<string, string> = {
  search: '搜索',
  detail: '详情',
  creator: '创作者',
};

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '排队中' },
  running: { color: 'processing', label: '运行中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
  cancelled: { color: 'warning', label: '已取消' },
};

function calcDuration(task: CrawlerTask): string {
  if (!task.started_at) return '—';
  const start = dayjs(task.started_at);
  const end = task.finished_at
    ? dayjs(task.finished_at)
    : task.status === 'running'
      ? dayjs()
      : null;
  if (!end) return '进行中';
  const sec = end.diff(start, 'second');
  if (sec < 60) return `${sec}秒`;
  if (sec < 3600) return `${Math.floor(sec / 60)}分${sec % 60}秒`;
  return `${Math.floor(sec / 3600)}时${Math.floor((sec % 3600) / 60)}分`;
}

export default function CrawlerPage() {
  const { message } = App.useApp();
  const [form] = Form.useForm<CrawlerStartPayload & { profile_id?: number }>();
  const queryClient = useQueryClient();

  // ---- 任务历史状态 ----
  const [activeTab, setActiveTab] = useState('launch');
  const [historyPage, setHistoryPage] = useState(1);
  const [historyStatus, setHistoryStatus] = useState<string | undefined>(undefined);
  const [detailTask, setDetailTask] = useState<CrawlerTask | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const { data: platforms } = useQuery({
    queryKey: ['config', 'platforms'],
    queryFn: fetchPlatforms,
  });

  const { data: options } = useQuery({
    queryKey: ['config', 'options'],
    queryFn: fetchConfigOptions,
  });

  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: fetchProfiles,
  });

  const { data: status, isLoading: statusLoading } = useCrawlerStatus(true);

  const isRunning = status?.status === 'running' || status?.status === 'stopping';

  // ---- 历史任务查询 ----
  const {
    data: taskData,
    isLoading: tasksLoading,
    isFetching: tasksFetching,
  } = useQuery({
    queryKey: ['crawler-tasks', historyPage, historyStatus],
    queryFn: () =>
      fetchCrawlerTasks({ page: historyPage, page_size: 20, status: historyStatus }),
    refetchInterval: activeTab === 'history' ? 10000 : false,
  });

  // ---- 启动任务 ----
  const startMutation = useMutation({
    mutationFn: startCrawler,
    onSuccess: (res) => {
      message.success(
        res.task_id ? `任务 #${res.task_id} 已启动` : '爬虫任务已启动',
      );
      void queryClient.invalidateQueries({ queryKey: ['crawler', 'status'] });
      void queryClient.invalidateQueries({ queryKey: ['crawler-tasks'] });
    },
  });

  const stopMutation = useMutation({
    mutationFn: stopCrawler,
    onSuccess: () => {
      message.success('已发送停止指令');
      void queryClient.invalidateQueries({ queryKey: ['crawler', 'status'] });
    },
  });

  // ---- 重新执行 ----
  const rerunMutation = useMutation({
    mutationFn: rerunCrawlerTask,
    onSuccess: (res) => {
      message.success(`任务 #${res.task_id} 已重新启动`);
      setDetailOpen(false);
      void queryClient.invalidateQueries({ queryKey: ['crawler', 'status'] });
      void queryClient.invalidateQueries({ queryKey: ['crawler-tasks'] });
    },
  });

  const profileId = Form.useWatch('profile_id', form);
  const crawlerType = Form.useWatch('crawler_type', form);

  useEffect(() => {
    if (!profiles?.length) return;
    const def = profiles.find((p) => p.is_default) ?? profiles[0];
    if (def && profileId == null) {
      form.setFieldsValue({
        profile_id: def.id,
        platform: def.payload.platform as PlatformCode,
        login_type: def.payload.login_type as LoginType,
        crawler_type: def.payload.crawler_type as CrawlerStartPayload['crawler_type'],
        keywords: def.payload.keywords,
        specified_ids: def.payload.specified_ids,
        creator_ids: def.payload.creator_ids,
        start_page: def.payload.start_page,
        enable_comments: def.payload.enable_comments,
        enable_sub_comments: def.payload.enable_sub_comments,
        headless: def.payload.headless,
        cookies: def.payload.cookies,
      });
    }
  }, [profiles, form, profileId]);

  const applyProfile = (id: number) => {
    const p = profiles?.find((x) => x.id === id);
    if (!p) return;
    form.setFieldsValue({
      profile_id: id,
      platform: p.payload.platform as PlatformCode,
      login_type: p.payload.login_type as LoginType,
      crawler_type: p.payload.crawler_type as CrawlerStartPayload['crawler_type'],
      keywords: p.payload.keywords,
      specified_ids: p.payload.specified_ids,
      creator_ids: p.payload.creator_ids,
      start_page: p.payload.start_page,
      enable_comments: p.payload.enable_comments,
      enable_sub_comments: p.payload.enable_sub_comments,
      headless: p.payload.headless,
      cookies: p.payload.cookies,
    });
  };

  const onFinish = (values: CrawlerStartPayload & { profile_id?: number }) => {
    startMutation.mutate(values);
  };

  // ---- 表格列定义 ----
  const taskColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '平台',
      key: 'platform',
      width: 80,
      render: (_: unknown, r: CrawlerTask) =>
        PLATFORM_LABELS[r.payload_snapshot?.platform] || r.payload_snapshot?.platform || '—',
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
        const cfg = STATUS_CONFIG[s] || { color: 'default', label: s };
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
      width: 140,
      render: (_: unknown, r: CrawlerTask) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              setDetailTask(r);
              setDetailOpen(true);
            }}
          >
            详情
          </Button>
          {r.status === 'failed' && (
            <Button
              type="link"
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                rerunMutation.mutate(r.id);
              }}
              loading={rerunMutation.isPending}
            >
              重跑
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="爬虫任务"
        description="启动爬虫或查看历史任务记录"
        extra={
          <Space>
            <Tag color={isRunning ? 'processing' : 'default'}>
              {statusLoading ? '…' : isRunning ? '运行中' : '空闲'}
            </Tag>
            {status?.task_id && <Tag>任务 #{status.task_id}</Tag>}
            <Button
              danger
              icon={<StopOutlined />}
              loading={stopMutation.isPending}
              disabled={!isRunning}
              onClick={() => stopMutation.mutate()}
            >
              停止
            </Button>
          </Space>
        }
      />

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="数据将保存至 MySQL"
        description="启动时会创建 crawler_task 记录，子进程通过 task_id 从数据库加载完整配置。"
      />

      <Tabs activeKey={activeTab} onChange={setActiveTab} destroyInactiveTabPane>
        {/* ==================== 启动任务 ==================== */}
        <Tabs.TabPane key="launch" tab="启动任务">
          <Card>
            <Form
              form={form}
              layout="vertical"
              onFinish={onFinish}
              disabled={isRunning}
            >
              <Form.Item name="profile_id" label="配置方案">
                <Select
                  placeholder="选择方案"
                  options={profiles?.map((p) => ({
                    value: p.id,
                    label: `${p.name}${p.is_default ? '（默认）' : ''}`,
                  }))}
                  onChange={applyProfile}
                />
              </Form.Item>

              <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                以下字段为本次任务的覆盖项（未改动的项沿用方案中的值）
              </Typography.Text>

              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item name="platform" label="平台" rules={[{ required: true }]}>
                    <Select
                      options={platforms?.platforms.map((p) => ({
                        value: p.value,
                        label: p.label,
                      }))}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item name="login_type" label="登录方式">
                    <Select options={options?.login_types} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item name="crawler_type" label="爬取模式">
                    <Select options={options?.crawler_types} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item name="start_page" label="起始页">
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item name="headless" label="无头模式" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              {crawlerType === 'search' && (
                <Form.Item name="keywords" label="搜索关键词" rules={[{ required: true }]}>
                  <Input placeholder="多个关键词用英文逗号分隔" />
                </Form.Item>
              )}
              {crawlerType === 'detail' && (
                <Form.Item name="specified_ids" label="帖子/视频 ID" rules={[{ required: true }]}>
                  <Input.TextArea rows={2} placeholder="多个 ID 用英文逗号分隔" />
                </Form.Item>
              )}
              {crawlerType === 'creator' && (
                <Form.Item name="creator_ids" label="创作者 ID" rules={[{ required: true }]}>
                  <Input.TextArea rows={2} placeholder="多个 ID 用英文逗号分隔" />
                </Form.Item>
              )}

              <Row gutter={16}>
                <Col>
                  <Form.Item name="enable_comments" label="抓取评论" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
                <Col>
                  <Form.Item name="enable_sub_comments" label="子评论" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item name="cookies" label="Cookie（可选）">
                <Input.TextArea rows={2} placeholder="login_type 为 cookie 时填写" />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<PlayCircleOutlined />}
                  loading={startMutation.isPending}
                  disabled={isRunning}
                >
                  启动爬虫
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Tabs.TabPane>

        {/* ==================== 历史记录 ==================== */}
        <Tabs.TabPane key="history" tab="历史记录">
          <Space style={{ marginBottom: 16 }}>
            <Select
              allowClear
              placeholder="状态过滤"
              style={{ width: 140 }}
              value={historyStatus}
              onChange={(val) => {
                setHistoryStatus(val);
                setHistoryPage(1);
              }}
              options={Object.entries(STATUS_CONFIG).map(([value, cfg]) => ({
                value,
                label: cfg.label,
              }))}
            />
            <Button
              icon={<ReloadOutlined />}
              loading={tasksFetching}
              onClick={() =>
                queryClient.invalidateQueries({ queryKey: ['crawler-tasks'] })
              }
            >
              刷新
            </Button>
          </Space>

          <Table
            rowKey="id"
            columns={taskColumns}
            dataSource={taskData?.items ?? []}
            loading={tasksLoading}
            pagination={{
              current: taskData?.page ?? historyPage,
              pageSize: taskData?.page_size ?? 20,
              total: taskData?.total ?? 0,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 条`,
              onChange: (p) => setHistoryPage(p),
            }}
            locale={{ emptyText: '暂无任务记录，请先启动爬虫' }}
            onRow={(r) => ({
              onClick: () => {
                setDetailTask(r);
                setDetailOpen(true);
              },
              style: { cursor: 'pointer' },
            })}
          />

          {/* 详情 Modal */}
          <Modal
            title={`任务 #${detailTask?.id ?? ''}`}
            open={detailOpen}
            onCancel={() => setDetailOpen(false)}
            width={720}
            footer={
              <Space>
                {detailTask?.status === 'failed' && (
                  <Button
                    type="primary"
                    icon={<ReloadOutlined />}
                    loading={rerunMutation.isPending}
                    onClick={() => rerunMutation.mutate(detailTask.id)}
                  >
                    重新执行
                  </Button>
                )}
                <Button onClick={() => setDetailOpen(false)}>关闭</Button>
              </Space>
            }
          >
            {detailTask && (
              <>
                <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="任务 ID">{detailTask.id}</Descriptions.Item>
                  <Descriptions.Item label="方案 ID">
                    {detailTask.profile_id ?? '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="平台">
                    {PLATFORM_LABELS[detailTask.payload_snapshot?.platform] ||
                      detailTask.payload_snapshot?.platform}
                  </Descriptions.Item>
                  <Descriptions.Item label="爬取类型">
                    {CRAWLER_TYPE_LABELS[detailTask.payload_snapshot?.crawler_type] ||
                      detailTask.payload_snapshot?.crawler_type}
                  </Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <Tag color={STATUS_CONFIG[detailTask.status]?.color}>
                      {STATUS_CONFIG[detailTask.status]?.label || detailTask.status}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="耗时">
                    {calcDuration(detailTask)}
                  </Descriptions.Item>
                  <Descriptions.Item label="创建时间">
                    {detailTask.created_at
                      ? dayjs(detailTask.created_at).format('YYYY-MM-DD HH:mm:ss')
                      : '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="开始时间">
                    {detailTask.started_at
                      ? dayjs(detailTask.started_at).format('YYYY-MM-DD HH:mm:ss')
                      : '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="结束时间">
                    {detailTask.finished_at
                      ? dayjs(detailTask.finished_at).format('YYYY-MM-DD HH:mm:ss')
                      : '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="错误信息" span={2}>
                    {detailTask.error_message || '—'}
                  </Descriptions.Item>
                </Descriptions>

                {detailTask.error_message && (
                  <Alert
                    type="error"
                    showIcon
                    message="任务失败原因"
                    description={detailTask.error_message}
                    style={{ marginBottom: 16 }}
                  />
                )}

                <Typography.Title level={5}>配置快照</Typography.Title>
                <pre
                  style={{
                    maxHeight: 400,
                    overflow: 'auto',
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 6,
                    fontSize: 12,
                    lineHeight: 1.5,
                  }}
                >
                  {JSON.stringify(detailTask.payload_snapshot, null, 2)}
                </pre>
              </>
            )}
          </Modal>
        </Tabs.TabPane>
      </Tabs>
    </>
  );
}
