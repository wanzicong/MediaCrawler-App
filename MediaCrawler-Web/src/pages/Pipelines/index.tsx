import { useState } from 'react';
import {
  Card, Tabs, Table, Tag, Button, Space, Form,
  Select, Input, message, Row, Col, Typography, Spin,
  Descriptions, Modal, Progress, Badge, Popconfirm,
} from 'antd';
import {
  ThunderboltOutlined, SendOutlined, PlusOutlined,
  ReloadOutlined, DeleteOutlined, PauseCircleOutlined,
  PlayCircleOutlined, ClockCircleOutlined, OrderedListOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import PageHeader from '@/components/PageHeader';
import {
  createPipeline, fetchPipelines, fetchPipeline,
  runPipeline, stopPipeline, deletePipeline,
} from '@/api/modules/pipelines';

const { TextArea } = Input;
const { Text } = Typography;

function PipelineList() {
  const qc = useQueryClient();
  const [detailId, setDetailId] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ['pipelines'],
    queryFn: fetchPipelines,
    refetchInterval: 5000,
  });

  const { data: detail } = useQuery({
    queryKey: ['pipeline-detail', detailId],
    queryFn: () => fetchPipeline(detailId!),
    enabled: !!detailId,
  });

  const runMut = useMutation({
    mutationFn: runPipeline,
    onSuccess: () => { message.success('管道已启动'); qc.invalidateQueries({ queryKey: ['pipelines'] }); },
  });
  const stopMut = useMutation({
    mutationFn: stopPipeline,
    onSuccess: () => { message.success('管道已停止'); qc.invalidateQueries({ queryKey: ['pipelines'] }); },
  });
  const delMut = useMutation({
    mutationFn: deletePipeline,
    onSuccess: () => { message.success('已删除'); qc.invalidateQueries({ queryKey: ['pipelines'] }); },
  });

  const modeLabel: Record<string, string> = { batch: '批量并行', queue: '排队串行', cron: '定时' };
  const statusColor: Record<string, string> = { idle: 'default', running: 'processing', completed: 'success', stopped: 'warning' };

  return (
    <>
      <Row gutter={[16, 16]}>
        {(data?.pipelines || []).map(p => (
          <Col xs={24} sm={12} lg={8} key={p.pipeline_id}>
            <Card size="small" hoverable onClick={() => setDetailId(p.pipeline_id)}
              title={<Space><NodeIndexOutlined />{p.name}</Space>}
              extra={
                <Space size="small">
                  {p.status === 'running' ? (
                    <Button size="small" icon={<PauseCircleOutlined />} onClick={(e) => { e.stopPropagation(); stopMut.mutate(p.pipeline_id); }}>停止</Button>
                  ) : (
                    <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={(e) => { e.stopPropagation(); runMut.mutate(p.pipeline_id); }}>执行</Button>
                  )}
                  <Button size="small" danger icon={<DeleteOutlined />} onClick={(e) => { e.stopPropagation(); delMut.mutate(p.pipeline_id); }} />
                </Space>
              }>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="平台"><Tag>{p.platform}</Tag></Descriptions.Item>
                <Descriptions.Item label="模式"><Tag color="blue">{modeLabel[p.mode] || p.mode}</Tag></Descriptions.Item>
                <Descriptions.Item label="关键词">{p.keywords_count} 个</Descriptions.Item>
                <Descriptions.Item label="状态"><Badge status={statusColor[p.status] as any} text={p.status} /></Descriptions.Item>
              </Descriptions>
              <Progress percent={p.total > 0 ? Math.round((p.progress / p.total) * 100) : 0} size="small" style={{ marginTop: 8 }} />
              <Text type="secondary" style={{ fontSize: 12 }}>{p.created_at}</Text>
            </Card>
          </Col>
        ))}
        {(!data?.pipelines || data.pipelines.length === 0) && (
          <Col span={24}><Card><Text type="secondary">暂无管道，请先创建</Text></Card></Col>
        )}
      </Row>

      <Modal title="管道详情" open={!!detailId} onCancel={() => setDetailId(null)} footer={null} width={700}>
        {detail ? (
          <Table dataSource={detail.tasks} columns={[
            { title: '#', dataIndex: 'ref', key: 'ref', width: 80 },
            { title: '关键词', dataIndex: 'keyword', key: 'keyword' },
            { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (v: string) => {
              const map: Record<string, { color: string; text: string }> = {
                pending: { color: 'default', text: '等待' }, running: { color: 'processing', text: '运行中' },
                completed: { color: 'success', text: '完成' }, failed: { color: 'error', text: '失败' },
              };
              const c = map[v] || { color: 'default', text: v };
              return <Tag color={c.color}>{c.text}</Tag>;
            }},
            { title: '任务ID', dataIndex: 'task_id', key: 'task_id', width: 80 },
            { title: '错误', dataIndex: 'error', key: 'error', ellipsis: true },
          ]} rowKey="ref" size="small" pagination={false} />
        ) : <Spin />}
      </Modal>
    </>
  );
}

function CreatePanel() {
  const qc = useQueryClient();
  const [form] = Form.useForm();
  const [keywordMode, setKeywordMode] = useState('manual');

  const createMut = useMutation({
    mutationFn: createPipeline,
    onSuccess: (res) => {
      message.success(`管道创建成功: ${res.pipeline_id}`);
      qc.invalidateQueries({ queryKey: ['pipelines'] });
      form.resetFields();
    },
  });

  const handleSubmit = (v: any) => {
    let keywords: string[] = [];
    if (keywordMode === 'manual') {
      keywords = (v.keywords_text || '').split(/[\n,]/).map((s: string) => s.trim()).filter(Boolean);
    } else {
      keywords = v.keyword_ids || [];
    }
    if (keywords.length === 0) { message.error('请输入关键词'); return; }
    createMut.mutate({
      name: v.name || `管道_${new Date().toLocaleTimeString()}`,
      platform: v.platform,
      keywords,
      mode: v.mode || 'batch',
      config: { crawler_type: 'search', save_option: 'db', headless: v.headless ?? true },
    });
  };

  return (
    <Row gutter={24}>
      <Col xs={24} lg={16}>
        <Card title="创建任务管道" size="small">
          <Form form={form} layout="vertical" onFinish={handleSubmit}
            initialValues={{ platform: 'xhs', mode: 'batch', headless: true }}>
            <Row gutter={16}>
              <Col span={12}><Form.Item name="name" label="管道名称"><Input placeholder="如：小红书国庆旅游关键词" /></Form.Item></Col>
              <Col span={6}><Form.Item name="platform" label="平台" rules={[{ required: true }]}>
                <Select options={['xhs','dy','ks','bili','wb','tieba','zhihu'].map(p => ({ label: p, value: p }))} />
              </Form.Item></Col>
              <Col span={6}><Form.Item name="mode" label="执行模式" rules={[{ required: true }]}>
                <Select options={[
                  { label: '批量并行', value: 'batch' }, { label: '排队串行', value: 'queue' },
                ]} />
              </Form.Item></Col>
            </Row>
            <Form.Item label="关键词输入">
              <Select value={keywordMode} onChange={setKeywordMode} style={{ width: 120, marginBottom: 8 }}
                options={[{ label: '手动输入', value: 'manual' }, { label: '从词库选择(待实现)', value: 'library', disabled: true }]} />
              {keywordMode === 'manual' && (
                <Form.Item name="keywords_text" noStyle rules={[{ required: true, message: '请输入关键词' }]}>
                  <TextArea rows={4} placeholder="每行一个关键词，或用逗号分隔" />
                </Form.Item>
              )}
            </Form.Item>
            <Button type="primary" htmlType="submit" icon={<PlusOutlined />} loading={createMut.isPending}>
              创建管道
            </Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} lg={8}>
        <Card title="模式说明" size="small">
          <Descriptions column={1} size="small">
            <Descriptions.Item label={<Tag color="blue">批量并行</Tag>}>所有关键词同时提交到调度器，最多3个并发</Descriptions.Item>
            <Descriptions.Item label={<Tag color="green">排队串行</Tag>}>一个关键词完成后，自动启动下一个，稳定可靠</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>
    </Row>
  );
}

export default function PipelinesPage() {
  const tabItems = [
    { key: 'list', label: <span><OrderedListOutlined /> 管道列表</span>, children: <PipelineList /> },
    { key: 'create', label: <span><PlusOutlined /> 创建管道</span>, children: <CreatePanel /> },
  ];
  return (
    <>
      <PageHeader title="任务管道" desc="关键词 → 任务模板 → 批量/排队自动执行，一键批量爬取" />
      <Tabs defaultActiveKey="list" items={tabItems} size="large" />
    </>
  );
}
