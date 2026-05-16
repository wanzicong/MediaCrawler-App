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
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined, StarOutlined } from '@ant-design/icons';
import { useState } from 'react';

import {
  createProfile,
  deleteProfile,
  fetchProfiles,
  putProfile,
  setDefaultProfile,
} from '@/api/modules/configMgmt';
import { fetchConfigOptions, fetchPlatforms } from '@/api';
import PageHeader from '@/components/PageHeader';
import type { CrawlerPayload, CrawlerProfile } from '@/types/config';
import { DEFAULT_PAYLOAD } from '@/types/config';

export default function SettingsPage() {
  const { message, modal } = App.useApp();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<CrawlerPayload & { name: string; description: string }>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CrawlerProfile | null>(null);

  const { data: profiles, isLoading } = useQuery({
    queryKey: ['profiles'],
    queryFn: fetchProfiles,
  });

  const { data: platforms } = useQuery({
    queryKey: ['config', 'platforms'],
    queryFn: fetchPlatforms,
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

  const columns = [
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

  return (
    <>
      <PageHeader
        title="配置方案"
        description="所有爬虫参数保存在 MySQL，启动任务时选择方案并可临时覆盖"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建方案
          </Button>
        }
      />

      <Card>
        <Typography.Paragraph type="secondary">
          数据存储固定为 MySQL（save_option=db）。敏感项如数据库密码请在服务端 .env 配置。
        </Typography.Paragraph>
        <Table<CrawlerProfile>
          rowKey="id"
          loading={isLoading}
          columns={columns}
          dataSource={profiles ?? []}
          pagination={false}
        />
      </Card>

      <Modal
        title={editing ? '编辑方案' : '新建方案'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => saveMutation.mutate()}
        confirmLoading={saveMutation.isPending}
        width={720}
        destroyOnClose
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
                            options={platforms?.platforms.map((p) => ({
                              value: p.value,
                              label: p.label,
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
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item name="crawler_max_notes_count" label="最大条数">
                          <InputNumber min={1} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="crawler_max_sleep_sec" label="间隔(秒)">
                          <InputNumber min={0} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
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
  );
}
