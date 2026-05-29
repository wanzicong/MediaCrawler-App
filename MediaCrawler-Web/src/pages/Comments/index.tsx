import { useState } from 'react';
import {
  Card, Tabs, Table, Tag, Button, Space, InputNumber, Form,
  Select, Input, message, Switch, Row, Col, Typography, Spin, Tooltip,
  Divider, Statistic, Progress,
} from 'antd';
import {
  MessageOutlined, ThunderboltOutlined, SendOutlined,
  ReloadOutlined, DeleteOutlined, HistoryOutlined,
  ClockCircleOutlined, ApiOutlined, SyncOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import PageHeader from '@/components/PageHeader';
import {
  commentSync, commentAsync, commentBatch,
  fetchCommentTasks, deleteCommentTask, fetchRateLimitStatus,
} from '@/api/modules/comments';

const { TextArea } = Input;
const { Text } = Typography;

function LaunchPanel() {
  const qc = useQueryClient();
  const [mode, setMode] = useState('async');
  const [form] = Form.useForm();

  const { data: rateStatus } = useQuery({
    queryKey: ['comment-rate-limit'],
    queryFn: fetchRateLimitStatus,
    refetchInterval: 5000,
  });

  const syncMut = useMutation({
    mutationFn: commentSync,
    onSuccess: (res) => {
      if (res.status === 'completed') {
        message.success(`同步完成: ${res.total} 条评论`);
      } else {
        message.error(`失败: ${res.error}`);
      }
    },
  });

  const asyncMut = useMutation({
    mutationFn: commentAsync,
    onSuccess: (res) => message.success(`任务已提交: ${res.task_id}`),
  });

  const batchMut = useMutation({
    mutationFn: commentBatch,
    onSuccess: (res) => message.success(`批量提交: ${res.count} 个任务`),
  });

  const handleSubmit = (v: any) => {
    const params: any = {
      platform: v.platform,
      max_comments: v.max_comments || 50,
      crawl_replies: v.crawl_replies || false,
    };
    if (mode === 'batch') {
      const lines = (v.post_input || '').split('\n').filter(Boolean);
      params.posts = lines.map((line: string) => {
        if (line.startsWith('http')) return { post_url: line.trim() };
        return { post_id: line.trim() };
      });
      if (params.posts.length === 0) { message.error('请输入帖子ID/URL'); return; }
      batchMut.mutate(params);
    } else {
      const input = (v.post_input || '').trim();
      if (!input) { message.error('请输入帖子ID或URL'); return; }
      if (input.startsWith('http')) params.post_url = input;
      else params.post_id = input;
      if (mode === 'sync') syncMut.mutate(params);
      else asyncMut.mutate(params);
    }
    qc.invalidateQueries({ queryKey: ['comment-tasks'] });
  };

  return (
    <Row gutter={24}>
      <Col xs={24} lg={16}>
        <Card title="新建评论爬取任务" size="small">
          <Form form={form} layout="vertical" onFinish={handleSubmit}
            initialValues={{ platform: 'xhs', mode: 'async', max_comments: 50 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="platform" label="平台" rules={[{ required: true }]}>
                  <Select options={['xhs','dy','ks','bili','wb','tieba','zhihu'].map(p => ({ label: p, value: p }))} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="模式">
                  <Select value={mode} onChange={setMode}
                    options={[
                      { label: '异步 (推荐)', value: 'async' },
                      { label: '同步 (等待结果)', value: 'sync' },
                      { label: '批量 (多个帖子)', value: 'batch' },
                    ]} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="max_comments" label="最大评论数">
                  <InputNumber min={10} max={500} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="post_input" label={mode === 'batch' ? '帖子ID/URL (每行一个)' : '帖子ID 或 URL'} rules={[{ required: true }]}>
              <TextArea rows={mode === 'batch' ? 4 : 2}
                placeholder={mode === 'batch' ? 'https://www.xiaohongshu.com/...\nhttps://www.xiaohongshu.com/...' : '帖子URL 或 帖子ID'} />
            </Form.Item>
            <Form.Item name="crawl_replies" label="爬取回复(子评论)" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Button type="primary" htmlType="submit"
              icon={<SendOutlined />}
              loading={syncMut.isPending || asyncMut.isPending || batchMut.isPending}>
              {mode === 'sync' ? '同步爬取' : mode === 'batch' ? '批量提交' : '提交异步任务'}
            </Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} lg={8}>
        <Card title="平台限流状态" size="small"
          extra={<Button size="small" icon={<ReloadOutlined />} onClick={() => qc.invalidateQueries({ queryKey: ['comment-rate-limit'] })} />}>
          {rateStatus ? Object.entries(rateStatus).map(([platform, status]) => (
            <div key={platform} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <Tag>{platform}</Tag>
                <Text type="secondary">{status.used_slots}/{status.max_slots} 槽位</Text>
              </div>
              <Progress percent={Math.round((status.available / status.max_burst) * 100)}
                size="small" status={status.available < 2 ? 'exception' : 'active'}
                format={() => `${Math.round(status.available)}/${status.max_burst}`} />
            </div>
          )) : <Spin />}
        </Card>
      </Col>
    </Row>
  );
}

function HistoryPanel() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['comment-tasks'],
    queryFn: () => fetchCommentTasks(50),
    refetchInterval: 5000,
  });

  const delMut = useMutation({
    mutationFn: deleteCommentTask,
    onSuccess: () => { message.success('已删除'); qc.invalidateQueries({ queryKey: ['comment-tasks'] }); },
  });

  const cols = [
    { title: 'ID', dataIndex: 'task_id', key: 'task_id', width: 80 },
    { title: '平台', dataIndex: 'platform', key: 'platform', width: 70, render: (v: string) => <Tag>{v}</Tag> },
    { title: '帖子ID', dataIndex: 'post_id', key: 'post_id', width: 120, ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (v: string) => {
      const map: Record<string, { color: string; text: string }> = {
        pending: { color: 'default', text: '等待' }, queued: { color: 'default', text: '排队' },
        running: { color: 'processing', text: '运行中' }, completed: { color: 'success', text: '完成' },
        failed: { color: 'error', text: '失败' },
      };
      const c = map[v] || { color: 'default', text: v };
      return <Tag color={c.color}>{c.text}</Tag>;
    }},
    { title: '评论数', dataIndex: 'total_crawled', key: 'total_crawled', width: 80 },
    { title: '创建', dataIndex: 'created_at', key: 'created_at', width: 100 },
    { title: '操作', key: 'act', width: 60, render: (_: any, r: any) => (
      <Button size="small" danger icon={<DeleteOutlined />} onClick={() => delMut.mutate(r.task_id)} />
    )},
  ];

  return (
    <Card title="任务历史" size="small" extra={
      <Button size="small" icon={<ReloadOutlined />} onClick={() => qc.invalidateQueries({ queryKey: ['comment-tasks'] })}>刷新</Button>
    }>
      <Table dataSource={data?.tasks || []} columns={cols} rowKey="task_id" size="small"
        pagination={false} loading={isLoading} locale={{ emptyText: '暂无评论任务' }} />
    </Card>
  );
}

export default function CommentsPage() {
  const tabItems = [
    { key: 'launch', label: <span><SendOutlined /> 新建任务</span>, children: <LaunchPanel /> },
    { key: 'history', label: <span><HistoryOutlined /> 任务历史</span>, children: <HistoryPanel /> },
  ];
  return (
    <>
      <PageHeader title="评论爬取" desc="独立爬取指定帖子/视频的评论数据，支持同步/异步/批量三种模式" />
      <Tabs defaultActiveKey="launch" items={tabItems} size="large" />
    </>
  );
}
