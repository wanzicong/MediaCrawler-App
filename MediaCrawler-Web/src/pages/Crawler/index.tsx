import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Alert,
  Button,
  Card,
  Form,
  Modal,
  Space,
  Tabs,
  Tag,
} from 'antd';
import { StopOutlined } from '@ant-design/icons';
import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  fetchConfigOptions,
  fetchEnabledPlatforms,
  startCrawler,
  stopCrawler,
  fetchCrawlerTasks,
  rerunCrawlerTask,
  deleteCrawlerTask,
  fetchTaskDataStats,
} from '@/api';
import { fetchProfiles } from '@/api/modules/configMgmt';
import PageHeader from '@/components/PageHeader';
import { useCrawlerStatus } from '@/hooks/useCrawlerStatus';
import { useCrawlerLogs } from '@/hooks/useCrawlerLogs';
import type { CrawlerStartPayload, LoginType, PlatformCode } from '@/types/api';
import type { CrawlerTask } from '@/types/config';

import CrawlerLaunchForm from './components/CrawlerLaunchForm';
import CrawlerTaskTable from './components/CrawlerTaskTable';
import CrawlerTaskDetailModal from './components/CrawlerTaskDetailModal';
import CrawlerLogViewer from './components/CrawlerLogViewer';

export default function CrawlerPage() {
  const { message, modal } = App.useApp();
  const [form] = Form.useForm<CrawlerStartPayload & { profile_id?: number }>();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('launch');
  const [historyPage, setHistoryPage] = useState(1);
  const [historyStatus, setHistoryStatus] = useState<string | undefined>(undefined);
  const [detailTask, setDetailTask] = useState<CrawlerTask | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const { data: platforms } = useQuery({
    queryKey: ['platforms', 'enabled'],
    queryFn: fetchEnabledPlatforms,
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

  // Real-time log WebSocket (connect whenever crawler is running)
  const { logs, connected, clearLogs, refreshLogs } = useCrawlerLogs(isRunning);

  const { data: taskData, isLoading: tasksLoading, isFetching: tasksFetching } = useQuery({
    queryKey: ['crawler-tasks', historyPage, historyStatus],
    queryFn: () =>
      fetchCrawlerTasks({ page: historyPage, page_size: 20, status: historyStatus }),
    placeholderData: keepPreviousData,
    refetchInterval: activeTab === 'history' ? 10000 : false,
  });

  const startMutation = useMutation({
    mutationFn: startCrawler,
    onSuccess: (res) => {
      message.success(res.task_id ? `任务 #${res.task_id} 已启动` : '爬虫任务已启动');
      setActiveTab('history');
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

  const rerunMutation = useMutation({
    mutationFn: rerunCrawlerTask,
    onSuccess: (res) => {
      message.success(`任务 #${res.task_id} 已重新启动`);
      setDetailOpen(false);
      void queryClient.invalidateQueries({ queryKey: ['crawler', 'status'] });
      void queryClient.invalidateQueries({ queryKey: ['crawler-tasks'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCrawlerTask,
    onSuccess: () => {
      message.success('任务已删除');
      setDetailOpen(false);
      void queryClient.invalidateQueries({ queryKey: ['crawler-tasks'] });
    },
  });

  const { data: taskStats, isLoading: statsLoading } = useQuery({
    queryKey: ['task-data-stats', detailTask?.id],
    queryFn: () => fetchTaskDataStats(detailTask!.id),
    enabled: !!detailTask && detailOpen,
  });

  const profileId = Form.useWatch('profile_id', form);

  useEffect(() => {
    if (!profiles?.length) return;
    const def = profiles.find((p) => p.is_default) ?? profiles[0];
    if (def && profileId == null) {
      const p = def.payload;
      form.setFieldsValue({
        profile_id: def.id,
        platform: p.platform as PlatformCode,
        login_type: p.login_type as LoginType,
        crawler_type: p.crawler_type as CrawlerStartPayload['crawler_type'],
        keywords: p.keywords,
        specified_ids: p.specified_ids,
        creator_ids: p.creator_ids,
        start_page: p.start_page,
        enable_comments: p.enable_comments,
        enable_sub_comments: p.enable_sub_comments,
        headless: p.headless,
        cookies: p.cookies,
      });
    }
  }, [profiles, form, profileId]);

  const applyProfile = (id: number) => {
    const pf = profiles?.find((x) => x.id === id);
    if (!pf) return;
    const p = pf.payload;
    form.setFieldsValue({
      profile_id: id,
      platform: p.platform as PlatformCode,
      login_type: p.login_type as LoginType,
      crawler_type: p.crawler_type as CrawlerStartPayload['crawler_type'],
      keywords: p.keywords,
      specified_ids: p.specified_ids,
      creator_ids: p.creator_ids,
      start_page: p.start_page,
      enable_comments: p.enable_comments,
      enable_sub_comments: p.enable_sub_comments,
      headless: p.headless,
      cookies: p.cookies,
    });
  };

  const onFinish = (values: CrawlerStartPayload & { profile_id?: number }) => {
    startMutation.mutate(values);
  };

  const handleRowClick = useCallback((task: CrawlerTask) => {
    setDetailTask(task);
    setDetailOpen(true);
  }, []);

  const handleRerun = useCallback((id: number) => rerunMutation.mutate(id), [rerunMutation.mutate]);

  const handleRefresh = useCallback(
    () => queryClient.invalidateQueries({ queryKey: ['crawler-tasks'] }),
    [queryClient],
  );

  const handleDelete = (taskId: number) => {
    modal.confirm({
      title: '确认删除',
      content: `确定要删除任务 #${taskId} 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => deleteMutation.mutate(taskId),
    });
  };

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

      <Card style={{ borderRadius: 12 }}>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        destroyInactiveTabPane
        tabBarStyle={{ marginBottom: 24, paddingLeft: 4 }}
        items={[
          {
            key: 'launch',
            label: '启动任务',
            children: (
              <CrawlerLaunchForm
                form={form}
                profiles={profiles}
                platforms={platforms?.map((p) => ({ value: p.code as PlatformCode, label: p.name, icon: p.icon }))}
                options={options}
                isRunning={isRunning}
                isPending={startMutation.isPending}
                applyProfile={applyProfile}
                onFinish={onFinish}
              />
            ),
          },
          {
            key: 'history',
            label: '历史记录',
            children: (
              <CrawlerTaskTable
                dataSource={taskData?.items ?? []}
                loading={tasksLoading}
                fetching={tasksFetching}
                statusFilter={historyStatus}
                page={taskData?.page ?? historyPage}
                total={taskData?.total ?? 0}
                pageSize={taskData?.page_size ?? 20}
                rerunPending={rerunMutation.isPending}
                onStatusChange={setHistoryStatus}
                onPageChange={setHistoryPage}
                onRowClick={handleRowClick}
                onRerun={handleRerun}
                onDelete={handleDelete}
                onRefresh={handleRefresh}
              />
            ),
          },
      ]}
      />

      <div style={{ marginTop: 20 }}>
        <CrawlerLogViewer
          logs={logs}
          connected={connected}
          onClear={clearLogs}
          onRefresh={refreshLogs}
        />
      </div>
      </Card>

      <CrawlerTaskDetailModal
        task={detailTask}
        open={detailOpen}
        stats={taskStats}
        statsLoading={statsLoading}
        rerunPending={rerunMutation.isPending}
        deletePending={deleteMutation.isPending}
        onClose={() => setDetailOpen(false)}
        onViewData={() => {
          setDetailOpen(false);
          navigate(
            `/data?task_id=${detailTask!.id}&platform=${detailTask!.payload_snapshot.platform}`,
          );
        }}
        onRerun={() => rerunMutation.mutate(detailTask!.id)}
        onDelete={() => {
          modal.confirm({
            title: '确认删除',
            content: `确定要删除任务 #${detailTask!.id} 吗？此操作不可恢复。`,
            okText: '删除',
            okType: 'danger',
            cancelText: '取消',
            onOk: () => deleteMutation.mutate(detailTask!.id),
          });
        }}
      />
    </>
  );
}
