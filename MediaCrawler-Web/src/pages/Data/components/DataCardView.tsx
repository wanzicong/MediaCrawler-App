import { Button, Card, Col, Empty, Image, Pagination, Row, Skeleton, Typography, Result, Space, Tag } from 'antd';
import { EyeOutlined, LikeOutlined, PlayCircleOutlined, CommentOutlined } from '@ant-design/icons';
import { CONTENT_ID_FIELDS } from '@/constants';
import { normalizeImageUrl, isImageUrl } from '@/utils/format';
import { FIELD_LABELS, IMAGE_FIELDS } from '@/constants';

interface Props {
  dataSource: Record<string, unknown>[];
  isLoading: boolean;
  isError: boolean;
  error?: Error | null;
  platform: string;
  kind: string;
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (p: number) => void;
  onPageSizeChange?: (size: number) => void;
  onCardClick: (row: Record<string, unknown>) => void;
  onViewComments: (contentId: string) => void;
}

const COVER_FIELDS = ['video_cover_url', 'cover_url', 'image_list'];
const AVATAR_FIELDS = ['avatar', 'user_avatar'];
const TITLE_FIELDS = ['title', 'content', 'desc', 'content_text'];
const STAT_FIELDS: Record<string, { icon: React.ReactNode; fields: string[] }> = {
  play: { icon: <PlayCircleOutlined />, fields: ['video_play_count', 'viewd_count'] },
  like: { icon: <LikeOutlined />, fields: ['liked_count', 'like_count'] },
  comment: { icon: <CommentOutlined />, fields: ['video_comment', 'comment_count', 'sub_comment_count'] },
};

function getFieldValue(row: Record<string, unknown>, fields: string[]): string | null {
  for (const f of fields) {
    const v = row[f];
    if (v != null && String(v) !== '') return String(v);
  }
  return null;
}

function getStatValue(row: Record<string, unknown>, fields: string[]): string | null {
  for (const f of fields) {
    const v = row[f];
    if (v != null && v !== '' && v !== '0') return String(v);
  }
  return null;
}

export default function DataCardView({
  dataSource, isLoading, isError, error, platform, kind, page, pageSize, total, onPageChange, onPageSizeChange, onCardClick, onViewComments,
}: Props) {
  if (isLoading) {
    return (
      <Row gutter={[16, 16]}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Col key={i} xs={24} sm={12} md={8} lg={6}>
            <Card><Skeleton active paragraph={{ rows: 3 }} /></Card>
          </Col>
        ))}
      </Row>
    );
  }

  if (isError) {
    return <Result status="error" title="数据加载失败" subTitle={(error as Error)?.message || '未知错误'} />;
  }

  if (dataSource.length === 0) {
    return <Empty description="暂无数据，请先完成至少一次爬取任务" />;
  }

  return (
    <>
      <Row gutter={[16, 16]}>
        {dataSource.map((row, idx) => {
          const coverUrl = getFieldValue(row, COVER_FIELDS);
          const avatarUrl = getFieldValue(row, AVATAR_FIELDS);
          const title = getFieldValue(row, TITLE_FIELDS) || '无标题';
          const nickname = String(row['nickname'] ?? row['user_nickname'] ?? '');
          const contentIdField = CONTENT_ID_FIELDS[platform] || 'note_id';
          const cid = row[contentIdField] as string | undefined;

          return (
            <Col key={String(row.id ?? idx)} xs={24} sm={12} md={8} lg={6}>
              <Card
                hoverable
                onClick={() => onCardClick(row)}
                cover={
                  coverUrl && isImageUrl(coverUrl) ? (
                    <div style={{ height: 160, overflow: 'hidden', background: '#f5f5f5' }}>
                      <Image
                        src={normalizeImageUrl(coverUrl)}
                        height={160}
                        width="100%"
                        style={{ objectFit: 'cover' }}
                        preview={false}
                        referrerPolicy="no-referrer"
                        fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIwIiBoZWlnaHQ9IjE2MCIgdmlld0JveD0iMCAwIDMyMCAxNjAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjMyMCIgaGVpZ2h0PSIxNjAiIGZpbGw9IiNFMkU4RjAiLz48L3N2Zz4="
                      />
                    </div>
                  ) : undefined
                }
                size="small"
              >
                <Typography.Paragraph
                  ellipsis={{ rows: 2 }}
                  style={{ marginBottom: 8, minHeight: 44, fontSize: 13, fontWeight: 500 }}
                >
                  {title}
                </Typography.Paragraph>

                <Space style={{ marginBottom: 4 }}>
                  {avatarUrl && isImageUrl(avatarUrl) && (
                    <Image
                      src={normalizeImageUrl(avatarUrl)}
                      width={20}
                      height={20}
                      style={{ borderRadius: 10, objectFit: 'cover' }}
                      preview={false}
                      referrerPolicy="no-referrer"
                      fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHJ4PSIxMCIgZmlsbD0iI0UyRThGMCIvPjwvc3ZnPg=="
                    />
                  )}
                  {nickname && (
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{nickname}</Typography.Text>
                  )}
                </Space>

                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 4 }}>
                  {Object.entries(STAT_FIELDS).map(([key, { icon, fields }]) => {
                    const val = getStatValue(row, fields);
                    if (!val) return null;
                    return (
                      <Tag key={key} style={{ margin: 0, fontSize: 11, lineHeight: '20px' }}>
                        {icon} {val}
                      </Tag>
                    );
                  })}
                </div>

                {kind === 'contents' && cid && (
                  <div style={{ marginTop: 8, textAlign: 'right' }}>
                    <Button
                      type="link"
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewComments(cid);
                      }}
                    >
                      查看评论
                    </Button>
                  </div>
                )}
              </Card>
            </Col>
          );
        })}
      </Row>

      <div style={{ marginTop: 16, textAlign: 'right' }}>
        <Pagination
          current={page}
          pageSize={pageSize}
          total={total}
          showSizeChanger
          pageSizeOptions={['10', '20', '50', '100', '200']}
          showTotal={(t) => `共 ${t} 条`}
          onChange={(p) => { onPageChange(p); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
          onShowSizeChange={(_current, size) => { onPageSizeChange?.(size); onPageChange(1); }}
        />
      </div>
    </>
  );
}
