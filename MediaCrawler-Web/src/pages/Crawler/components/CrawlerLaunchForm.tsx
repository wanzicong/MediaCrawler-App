import { useRef } from 'react';
import type { FormInstance } from 'antd';
import {
  App,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Switch,
  Typography,
} from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import type { ConfigOptionsResponse, CrawlerStartPayload, PlatformItem } from '@/types/api';
import type { CrawlerProfile } from '@/types/config';

interface Props {
  form: FormInstance<CrawlerStartPayload & { profile_id?: number }>;
  profiles?: CrawlerProfile[];
  platforms?: PlatformItem[];
  options?: ConfigOptionsResponse;
  isRunning: boolean;
  isPending: boolean;
  applyProfile: (id: number) => void;
  onFinish: (values: CrawlerStartPayload & { profile_id?: number }) => void;
}

export default function CrawlerLaunchForm({
  form,
  profiles,
  platforms,
  options,
  isRunning,
  isPending,
  applyProfile,
  onFinish,
}: Props) {
  const { modal } = App.useApp();
  const crawlerType = Form.useWatch('crawler_type', form);
  const dirtyRef = useRef(false);

  const handleProfileChange = (id: number) => {
    if (dirtyRef.current) {
      modal.confirm({
        title: '切换方案',
        content: '当前表单已有修改，切换方案将覆盖这些修改。确定继续？',
        okText: '确定',
        cancelText: '取消',
        onOk: () => {
          dirtyRef.current = false;
          applyProfile(id);
        },
      });
    } else {
      applyProfile(id);
    }
  };

  return (
    <Card>
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        onValuesChange={() => {
          dirtyRef.current = true;
        }}
        disabled={isRunning}
      >
        <Form.Item name="profile_id" label="配置方案">
          <Select
            placeholder="选择方案"
            options={profiles?.map((p) => ({
              value: p.id,
              label: `${p.name}${p.is_default ? '（默认）' : ''}`,
            }))}
            onChange={handleProfileChange}
          />
        </Form.Item>

        <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          以下字段为本次任务的覆盖项（未改动的项沿用方案中的值）
        </Typography.Text>

        <Row gutter={16}>
          <Col xs={24} md={8}>
            <Form.Item name="platform" label="平台" rules={[{ required: true }]}>
              <Select
                options={platforms?.map((p) => ({
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
            <Form.Item name="headless" valuePropName="checked">
              <Switch checkedChildren="无头" unCheckedChildren="有头" />
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
            <Form.Item name="enable_comments" valuePropName="checked">
              <Switch checkedChildren="抓评论" unCheckedChildren="关评论" />
            </Form.Item>
          </Col>
          <Col>
            <Form.Item name="enable_sub_comments" valuePropName="checked">
              <Switch checkedChildren="子评论" unCheckedChildren="无子评论" />
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
            loading={isPending}
            disabled={isRunning}
          >
            启动爬虫
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
