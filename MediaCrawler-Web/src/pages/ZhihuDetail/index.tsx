import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import {
  App, Button, Card, Descriptions, Divider, Skeleton, Space, Tag, Typography, Result, Empty,
} from 'antd';
import {
  ArrowLeftOutlined, ExportOutlined, LikeOutlined, CommentOutlined, ClockCircleOutlined, UserOutlined,
} from '@ant-design/icons';
import { fetchDbData } from '@/api';
import PageHeader from '@/components/PageHeader';
import { FIELD_LABELS, ZHIHU_CONTENT_TYPE_LABELS } from '@/constants';
import { formatText } from '@/utils/format';

function sanitizeHtml(html: string): string {
  if (!html) return '';
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    .replace(/\son\w+\s*=\s*"[^"]*"/gi, '')
    .replace(/\son\w+\s*=\s*'[^']*'/gi, '');
}

export default function ZhihuDetailPage() {
  const { contentId } = useParams<{ contentId: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['zhihu-detail', contentId],
    queryFn: async () => {
      const res = await fetchDbData('zhihu', 'contents', {
        content_id: contentId!,
        page_size: 1,
      });
      if (!res.items?.length) throw new Error('内容不存在或已被删除');
      return res.items[0] as Record<string, unknown>;
    },
    enabled: !!contentId,
    retry: false,
  });

  if (isLoading) {
    return (
      <>
        <PageHeader title="知乎详情" description="加载中..." />
        <Card><Skeleton active paragraph={{ rows: 12 }} /></Card>
      </>
    );
  }

  if (isError || !data) {
    return (
      <>
        <PageHeader title="知乎详情" description="内容阅读" />
        <Result
          status="error"
          title="加载失败"
          subTitle={(error as Error)?.message || '未知错误'}
          extra={<Button onClick={() => navigate(-1)}>返回</Button>}
        />
      </>
    );
  }

  const contentType = String(data.content_type || 'answer');
  const typeInfo = ZHIHU_CONTENT_TYPE_LABELS[contentType] || { label: contentType, color: 'default' };
  const title = String(data.title || '无标题');
  const rawHtml = String(data.content_html || '');
  const plainText = String(data.content_text || '');
  const hasHtml = rawHtml.length > 0;
  const contentBody = hasHtml ? sanitizeHtml(rawHtml) : plainText;
  const isHtmlRender = hasHtml;

  return (
    <>
      <PageHeader
        title="知乎详情"
        description="内容阅读"
        extra={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
            {data.content_url && (
              <Button
                icon={<ExportOutlined />}
                onClick={() => window.open(String(data.content_url), '_blank', 'noopener')}
              >
                查看原文
              </Button>
            )}
          </Space>
        }
      />

      <Card style={{ borderRadius: 12 }}>
        {/* 标题区 */}
        <div style={{ marginBottom: 16 }}>
          <Space style={{ marginBottom: 8 }}>
            <Tag color={typeInfo.color} style={{ fontSize: 13, padding: '2px 10px' }}>{typeInfo.label}</Tag>
            {hasHtml ? (
              <Tag color="processing">HTML 格式</Tag>
            ) : (
              <Tag>纯文本</Tag>
            )}
          </Space>
          <Typography.Title level={4} style={{ margin: 0 }}>{title}</Typography.Title>
        </div>

        {/* 作者 + 统计 */}
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 20,
          padding: '12px 16px', background: '#fafafa', borderRadius: 8,
        }}>
          <Space>
            <UserOutlined />
            <Typography.Text strong>{String(data.user_nickname || '未知作者')}</Typography.Text>
          </Space>
          <Space>
            <LikeOutlined />
            <span>{data.voteup_count ?? 0} 赞同</span>
          </Space>
          <Space>
            <CommentOutlined />
            <span>{data.comment_count ?? 0} 评论</span>
          </Space>
          <Space>
            <ClockCircleOutlined />
            <span>{formatText('created_time', data.created_time)}</span>
          </Space>
        </div>

        <Divider style={{ margin: '0 0 20px 0' }} />

        {/* 内容正文 */}
        {isHtmlRender ? (
          <div
            style={{
              fontSize: 15, lineHeight: 1.85, color: '#333',
              wordBreak: 'break-word', overflowWrap: 'break-word',
              maxWidth: '100%',
            }}
            dangerouslySetInnerHTML={{ __html: contentBody }}
          />
        ) : (
          <Typography.Paragraph
            style={{
              fontSize: 15, lineHeight: 1.85, whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {contentBody || '（无内容）'}
          </Typography.Paragraph>
        )}

        <Divider style={{ margin: '20px 0' }} />

        {/* 元数据 */}
        <Descriptions
          bordered
          size="small"
          column={{ xs: 1, sm: 2, lg: 3 }}
          title="详细信息"
        >
          {(['content_id', 'question_id', 'content_type', 'content_url', 'source_keyword', 'created_time', 'updated_time', 'voteup_count', 'comment_count'] as const).map((key) => {
            const v = data[key];
            if (v == null || v === '') return null;
            return (
              <Descriptions.Item key={key} label={FIELD_LABELS[key] || key}>
                {key === 'content_url' ? (
                  <Typography.Link href={String(v)} target="_blank" rel="noopener noreferrer" ellipsis>
                    {String(v)}
                  </Typography.Link>
                ) : (
                  formatText(key, v)
                )}
              </Descriptions.Item>
            );
          })}
        </Descriptions>
      </Card>
    </>
  );
}
