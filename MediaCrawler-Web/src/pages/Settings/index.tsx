import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Skeleton,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  AndroidOutlined,
  BookOutlined,
  CommentOutlined,
  CustomerServiceOutlined,
  DeleteOutlined,
  EditOutlined,
  GlobalOutlined,
  MenuOutlined,
  MessageOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
  StarOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import { useEffect, useState, createElement } from 'react';

import {
  createProfile,
  deleteProfile,
  fetchProfiles,
  putProfile,
  setDefaultProfile,
} from '@/api/modules/configMgmt';
import {
  fetchConfigOptions,
  fetchEnabledPlatforms,
  fetchAllPlatforms,
  updatePlatform,
  reorderPlatforms,
} from '@/api';
import type { PlatformInfo } from '@/api';
import PageHeader from '@/components/PageHeader';
import type { CrawlerPayload, CrawlerProfile } from '@/types/config';
import { DEFAULT_PAYLOAD } from '@/types/config';

export default function SettingsPage() {
  const { message, modal } = App.useApp();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<CrawlerPayload & { name: string; description: string }>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CrawlerProfile | null>(null);
  const [activeTab, setActiveTab] = useState('profiles');

  /* ──────── 配置方案 ──────── */
  const { data: profiles, isLoading } = useQuery({
    queryKey: ['profiles'],
    queryFn: fetchProfiles,
  });

  const { data: enabledPlatforms } = useQuery({
    queryKey: ['platforms', 'enabled'],
    queryFn: fetchEnabledPlatforms,
  });

  const { data: options } = useQuery({
    queryKey: ['config', 'options'],
    queryFn: fetchConfigOptions,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const values = await form.validateFields();
      const { name, description, ...payload } = values;
      if (editing) {
        return putProfile(editing.id, {
          name,
          description,
          payload: { ...payload, save_option: 'db' },
        });
      }
      return createProfile({
        name,
        description,
        payload: { ...payload, save_option: 'db' },
      });
    },
    onSuccess: () => {
      message.success(editing ? '已更新方案' : '已创建方案');
      setModalOpen(false);
      void queryClient.invalidateQueries({ queryKey: ['profiles'] });
    },
  });

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({
      name: '',
      description: '',
      ...DEFAULT_PAYLOAD,
    });
    setModalOpen(true);
  };

  const openEdit = (record: CrawlerProfile) => {
    setEditing(record);
    form.setFieldsValue({
      name: record.name,
      description: record.description,
      ...record.payload,
    });
    setModalOpen(true);
  };

  const crawlerType = Form.useWatch('crawler_type', form);

  const profileColumns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: '平台',
      key: 'platform',
      render: (_: unknown, r: CrawlerProfile) => r.payload.platform,
    },
    {
      title: '模式',
      key: 'crawler_type',
      render: (_: unknown, r: CrawlerProfile) => r.payload.crawler_type,
    },
    {
      title: '默认',
      dataIndex: 'is_default',
      render: (v: boolean) => (v ? <Tag color="blue">默认</Tag> : null),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: CrawlerProfile) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          {!record.is_default && (
            <Button
              type="link"
              icon={<StarOutlined />}
              onClick={() =>
                setDefaultProfile(record.id).then(() => {
                  message.success('已设为默认');
                  void queryClient.invalidateQueries({ queryKey: ['profiles'] });
                })
              }
            >
              设为默认
            </Button>
          )}
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            disabled={record.is_default}
            onClick={() =>
              modal.confirm({
                title: '确认删除该方案？',
                onOk: () =>
                  deleteProfile(record.id).then(() => {
                    message.success('已删除');
                    void queryClient.invalidateQueries({ queryKey: ['profiles'] });
                  }),
              })
            }
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  /* ──────── 平台管理 ──────── */

  // 后端图标名 → Ant Design 图标组件映射
  const iconMap: Record<string, React.ReactNode> = {
    'book-open': createElement(BookOutlined),
    music: createElement(CustomerServiceOutlined),
    video: createElement(VideoCameraOutlined),
    tv: createElement(PlayCircleOutlined),
    'message-circle': createElement(MessageOutlined),
    'messages-square': createElement(CommentOutlined),
    'help-circle': createElement(QuestionCircleOutlined),
    appstore: createElement(GlobalOutlined),
    android: createElement(AndroidOutlined),
  };

  const { data: allPlatforms, isLoading: platformsLoading } = useQuery({
    queryKey: ['platforms', 'all'],
    queryFn: fetchAllPlatforms,
  });

  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [savingOrder, setSavingOrder] = useState(false);

  useEffect(() => {
    if (allPlatforms) {
      setPlatforms([...allPlatforms].sort((a, b) => a.sort_order - b.sort_order));
    }
  }, [allPlatforms]);

  const handleDragStart = (index: number) => setDragIndex(index);

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (dragIndex === null || dragIndex === index) return;
    const newList = [...platforms];
    const [item] = newList.splice(dragIndex, 1);
    newList.splice(index, 0, item);
    setPlatforms(newList);
    setDragIndex(index);
  };

  const handleDragEnd = () => setDragIndex(null);

  const handleSaveOrder = async () => {
    setSavingOrder(true);
    try {
      await reorderPlatforms(platforms.map((p) => p.id));
      message.success('排序已保存');
      void queryClient.invalidateQueries({ queryKey: ['platforms', 'all'] });
    } catch {
      // error already handled by interceptor
    } finally {
      setSavingOrder(false);
    }
  };

  const startEdit = (p: PlatformInfo) => {
    setEditingId(p.id);
    setEditName(p.name);
  };

  const saveEdit = async (id: number) => {
    if (!editName.trim()) {
      setEditingId(null);
      return;
    }
    const name = editName.trim();
    // Optimistic update local state
    setPlatforms((prev) => prev.map((p) => (p.id === id ? { ...p, name } : p)));
    setEditingId(null);
    try {
      await updatePlatform(id, { name });
      void queryClient.invalidateQueries({ queryKey: ['platforms', 'all'] });
      void queryClient.invalidateQueries({ queryKey: ['platforms', 'enabled'] });
    } catch {
      // revert on error handled by refetch
      void queryClient.invalidateQueries({ queryKey: ['platforms', 'all'] });
    }
  };

  const toggleEnabled = async (id: number, enabled: boolean) => {
    // Optimistic update
    setPlatforms((prev) => prev.map((p) => (p.id === id ? { ...p, enabled } : p)));
    try {
      await updatePlatform(id, { enabled });
      void queryClient.invalidateQueries({ queryKey: ['platforms', 'all'] });
      void queryClient.invalidateQueries({ queryKey: ['platforms', 'enabled'] });
    } catch {
      void queryClient.invalidateQueries({ queryKey: ['platforms', 'all'] });
    }
  };

  return (
    <>
      <PageHeader title="设置" />

      <Card style={{ borderRadius: 12 }}>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        tabBarStyle={{ marginBottom: 24, paddingLeft: 4 }}
        items={[
          {
            key: 'profiles',
            label: '配置方案',
            children: (
              <>
                <div style={{ marginBottom: 16 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
                    新建方案
                  </Button>
                </div>

                <Card>
                  <Typography.Paragraph type="secondary">
                    数据存储固定为 MySQL（save_option=db）。敏感项如数据库密码请在服务端 .env 配置。
                  </Typography.Paragraph>
                  {isLoading ? (
                    <Skeleton active paragraph={{ rows: 6 }} />
                  ) : (
                    <Table<CrawlerProfile>
                      rowKey="id"
                      columns={profileColumns}
                      dataSource={profiles ?? []}
                      pagination={false}
                    />
                  )}
                </Card>

                <Modal
                  title={editing ? '编辑方案' : '新建方案'}
                  open={modalOpen}
                  onCancel={() => setModalOpen(false)}
                  onOk={() => saveMutation.mutate()}
                  confirmLoading={saveMutation.isPending}
                  width={720}
                  destroyOnHidden
                >
                  <Form form={form} layout="vertical">
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="name" label="方案名称" rules={[{ required: true }]}>
                          <Input />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="description" label="说明">
                          <Input />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Tabs
                      items={[
                        {
                          key: 'basic',
                          label: '基础',
                          children: (
                            <>
                              <Row gutter={16}>
                                <Col span={8}>
                                  <Form.Item name="platform" label="平台" rules={[{ required: true }]}>
                                    <Select
                                      options={enabledPlatforms?.map((p) => ({
                                        value: p.code,
                                        label: p.name,
                                      }))}
                                    />
                                  </Form.Item>
                                </Col>
                                <Col span={8}>
                                  <Form.Item name="login_type" label="登录">
                                    <Select options={options?.login_types} />
                                  </Form.Item>
                                </Col>
                                <Col span={8}>
                                  <Form.Item name="crawler_type" label="模式">
                                    <Select options={options?.crawler_types} />
                                  </Form.Item>
                                </Col>
                              </Row>
                              {crawlerType === 'search' && (
                                <Form.Item name="keywords" label="关键词">
                                  <Input placeholder="逗号分隔" />
                                </Form.Item>
                              )}
                              {crawlerType === 'detail' && (
                                <Form.Item name="specified_ids" label="帖子/视频 ID">
                                  <Input.TextArea rows={2} />
                                </Form.Item>
                              )}
                              {crawlerType === 'creator' && (
                                <Form.Item name="creator_ids" label="创作者 ID">
                                  <Input.TextArea rows={2} />
                                </Form.Item>
                              )}
                              <Row gutter={16}>
                                <Col span={8}>
                                  <Form.Item name="start_page" label="起始页">
                                    <InputNumber min={1} style={{ width: '100%' }} />
                                  </Form.Item>
                                </Col>
                                <Col span={8}>
                                  <Form.Item name="headless" label="无头" valuePropName="checked">
                                    <Switch />
                                  </Form.Item>
                                </Col>
                              </Row>
                              <Form.Item name="cookies" label="Cookie">
                                <Input.TextArea rows={2} />
                              </Form.Item>
                            </>
                          ),
                        },
                        {
                          key: 'comment',
                          label: '评论',
                          children: (
                            <Row gutter={16}>
                              <Col>
                                <Form.Item name="enable_comments" valuePropName="checked">
                                  <Switch checkedChildren="抓评论" unCheckedChildren="关评论" />
                                </Form.Item>
                              </Col>
                              <Col>
                                <Form.Item name="enable_sub_comments" valuePropName="checked">
                                  <Switch checkedChildren="子评论" unCheckedChildren="无子评论" />
                                </Form.Item>
                              </Col>
                              <Col span={12}>
                                <Form.Item name="crawler_max_comments_count_singlenotes" label="单条最大评论数">
                                  <InputNumber min={1} style={{ width: '100%' }} />
                                </Form.Item>
                              </Col>
                            </Row>
                          ),
                        },
                        {
                          key: 'advanced',
                          label: '高级',
                          children: (
                            <>
                              <Row gutter={16}>
                                <Col>
                                  <Form.Item name="enable_cdp_mode" valuePropName="checked">
                                    <Switch checkedChildren="CDP" unCheckedChildren="CDP关" />
                                  </Form.Item>
                                </Col>
                                <Col>
                                  <Form.Item name="enable_ip_proxy" valuePropName="checked">
                                    <Switch checkedChildren="代理" unCheckedChildren="无代理" />
                                  </Form.Item>
                                </Col>
                                <Col>
                                  <Form.Item name="enable_get_medias" valuePropName="checked">
                                    <Switch checkedChildren="媒体" unCheckedChildren="无媒体" />
                                  </Form.Item>
                                </Col>
                                <Col>
                                  <Form.Item name="save_login_state" valuePropName="checked">
                                    <Switch checkedChildren="存登录" unCheckedChildren="不存登录" />
                                  </Form.Item>
                                </Col>
                              </Row>
                              <Row gutter={[16, 8]}>
                                <Col xs={12} sm={6}>
                                  <Form.Item name="crawler_max_notes_count" label="最大条数">
                                    <InputNumber min={1} style={{ width: '100%' }} />
                                  </Form.Item>
                                </Col>
                                <Col xs={12} sm={6}>
                                  <Form.Item name="crawler_max_sleep_sec" label="最小间隔(秒)">
                                    <InputNumber min={0} style={{ width: '100%' }} />
                                  </Form.Item>
                                </Col>
                                <Col xs={12} sm={6}>
                                  <Form.Item name="crawler_max_sleep_sec_max" label="最大间隔(秒)">
                                    <InputNumber min={0} style={{ width: '100%' }} />
                                  </Form.Item>
                                </Col>
                                <Col xs={12} sm={6}>
                                  <Form.Item name="ip_proxy_pool_count" label="代理池">
                                    <InputNumber min={1} style={{ width: '100%' }} />
                                  </Form.Item>
                                </Col>
                              </Row>
                            </>
                          ),
                        },
                      ]}
                    />
                  </Form>
                </Modal>
              </>
            ),
          },
          {
            key: 'platforms',
            label: '平台管理',
            children: (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <Typography.Text strong style={{ fontSize: 15 }}>平台列表</Typography.Text>
                  <Button type="primary" loading={savingOrder} onClick={handleSaveOrder}>
                    保存排序
                  </Button>
                </div>
                <Typography.Paragraph type="secondary" style={{ marginBottom: 20 }}>
                  拖拽平台行可调整排序，点击名称可编辑，启用/禁用控制平台在爬虫任务中是否可选。
                </Typography.Paragraph>
                {platformsLoading ? (
                  <Skeleton active paragraph={{ rows: 6 }} />
                ) : (
                  <div>
                    {/* table header */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '10px 16px',
                        borderBottom: '2px solid #f0f0f0',
                        fontWeight: 600,
                        color: '#94A3B8',
                        fontSize: 12,
                        textTransform: 'uppercase',
                        letterSpacing: 0.5,
                      }}
                    >
                      <span style={{ width: 36, flexShrink: 0 }} />
                      <span style={{ width: 36, flexShrink: 0 }} />
                      <span style={{ flex: 2, minWidth: 0 }}>平台名称</span>
                      <span style={{ flex: 1, minWidth: 0 }}>编码</span>
                      <span style={{ width: 60, textAlign: 'center', flexShrink: 0 }}>排序</span>
                      <span style={{ width: 60, textAlign: 'center', flexShrink: 0 }}>启用</span>
                    </div>

                    {platforms.map((p, index) => (
                      <div
                        key={p.id}
                        draggable
                        onDragStart={() => handleDragStart(index)}
                        onDragOver={(e) => handleDragOver(e, index)}
                        onDragEnd={handleDragEnd}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '10px 16px',
                          borderBottom: '1px solid #f5f5f5',
                          opacity: dragIndex === index ? 0.4 : p.enabled ? 1 : 0.45,
                          transition: 'all 0.2s',
                          background: dragIndex === index ? '#F8FAFC' : '#fff',
                          borderRadius: dragIndex === index ? 8 : 0,
                        }}
                      >
                        {/* drag handle */}
                        <span
                          style={{ width: 36, cursor: 'grab', color: '#CBD5E1', fontSize: 16, flexShrink: 0 }}
                        >
                          <MenuOutlined />
                        </span>

                        {/* icon */}
                        <span style={{ width: 36, fontSize: 18, flexShrink: 0, color: '#6366F1' }}>
                          {iconMap[p.icon] || <GlobalOutlined />}
                        </span>

                        {/* name (inline editable) */}
                        <span style={{ flex: 2, minWidth: 0, paddingRight: 12 }}>
                          {editingId === p.id ? (
                            <Input
                              size="small"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              onPressEnter={() => saveEdit(p.id)}
                              onBlur={() => saveEdit(p.id)}
                              autoFocus
                              style={{ maxWidth: 160 }}
                              onKeyDown={(e) => {
                                if (e.key === 'Escape') setEditingId(null);
                              }}
                            />
                          ) : (
                            <Typography.Text
                              style={{ cursor: 'pointer', fontWeight: 500 }}
                              onClick={() => startEdit(p)}
                            >
                              {p.name}
                            </Typography.Text>
                          )}
                        </span>

                        {/* code */}
                        <span style={{ flex: 1, minWidth: 0 }}>
                          <Tag style={{ fontSize: 12 }}>{p.code}</Tag>
                        </span>

                        {/* sort_order */}
                        <span style={{ width: 60, textAlign: 'center', color: '#94A3B8', fontSize: 13, flexShrink: 0 }}>
                          {index + 1}
                        </span>

                        {/* enabled switch */}
                        <span style={{ width: 60, textAlign: 'center', flexShrink: 0 }}>
                          <Switch
                            size="small"
                            checked={p.enabled}
                            onChange={(checked) => toggleEnabled(p.id, checked)}
                          />
                        </span>
                      </div>
                    ))}

                    {platforms.length === 0 && !platformsLoading && (
                      <div style={{ textAlign: 'center', padding: 32, color: '#999' }}>
                        暂无平台数据
                      </div>
                    )}
                  </div>
                )}
              </>),
          },
        ]}
      />
      </Card>
    </>
  );
}
