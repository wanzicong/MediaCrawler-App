import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import {
  App, Button, Card, Descriptions, Divider, Skeleton, Space, Tag, Typography, Result, Empty, Tooltip,
} from 'antd';
import {
  ArrowLeftOutlined, ExportOutlined, LikeOutlined, CommentOutlined, ClockCircleOutlined,
  UserOutlined, RocketOutlined, RobotOutlined, PlusOutlined, CheckOutlined,
  LeftOutlined, RightOutlined, PushpinOutlined,
} from '@ant-design/icons';
import { fetchDbData } from '@/api';
import { fetchContentNeighbors } from '@/api/modules/dataDb';
import { startCrawler } from '@/api/modules/crawler';
import { analyzeContent } from '@/api/modules/ai';
import type { ContentAnalysisResponse } from '@/api/modules/ai';
import { batchCreateKeywords } from '@/api/modules/keywords';
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
  const returnPath = sessionStorage.getItem('dataPageReturnUrl') || '/data';
  const { message, modal } = App.useApp();

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

  // 爬取当前作者全部信息
  const crawlCreatorMut = useMutation({
    mutationFn: (creatorId: string) =>
      startCrawler({
        platform: 'zhihu',
        crawler_type: 'creator',
        creator_ids: creatorId,
        execute_now: true,
      }),
    onSuccess: (res) => {
      message.success(`作者爬取任务已启动 (ID: ${res.task_id})`);
    },
  });

  const handleCrawlCreator = () => {
    const urlToken = (data?.user_url_token as string) || '';
    const userLink = (data?.user_link as string) || '';
    let creatorId = urlToken || userLink?.split('/').pop() || '';
    creatorId = creatorId?.split('?')[0] || '';
    if (!creatorId) {
      message.warning('无法获取作者ID');
      return;
    }
    modal.confirm({
      title: '爬取作者全部信息',
      content: `确认对作者「${(data?.user_nickname as string) || creatorId}」启动爬取任务？将爬取其所有回答/文章/视频。`,
      okText: '启动爬取',
      cancelText: '取消',
      onOk: () => crawlCreatorMut.mutate(creatorId),
    });
  };

  // ── AI 内容分析 ──────────────────────────────────────────────
  const [aiResult, setAiResult] = useState<ContentAnalysisResponse | null>(null);
  const [addedKeywords, setAddedKeywords] = useState<Set<string>>(new Set());

  const analyzeMut = useMutation({
    mutationFn: () => analyzeContent({ platform: 'zhihu', content_id: contentId! }),
    onSuccess: (res) => {
      setAiResult(res);
      message.success('AI 分析完成');
    },
    onError: (err: Error) => {
      message.error(err.message || 'AI 分析失败');
    },
  });

  const addKeywordsMut = useMutation({
    mutationFn: (keywords: string[]) =>
      batchCreateKeywords({ keywords, platform: 'zhihu' }),
    onSuccess: (_, keywords) => {
      setAddedKeywords((prev) => {
        const next = new Set(prev);
        keywords.forEach((k) => next.add(k));
        return next;
      });
      message.success(`已添加 ${keywords.length} 个关键词到关键词库`);
    },
    onError: (err: Error) => {
      message.error(err.message || '添加关键词失败');
    },
  });

  const handleAddKeyword = (keyword: string) => {
    addKeywordsMut.mutate([keyword]);
  };

  const handleAddAllKeywords = () => {
    if (!aiResult?.keywords?.length) return;
    const remaining = aiResult.keywords.filter((k) => !addedKeywords.has(k));
    if (remaining.length === 0) {
      message.info('所有关键词已添加');
      return;
    }
    addKeywordsMut.mutate(remaining);
  };

  // ── 上一条 / 下一条导航 ──────────────────────────────────────

  // 从 sessionStorage 读取列表上下文
  const pageItems: string[] = useMemo(() => {
    try {
      const raw = sessionStorage.getItem('zhihu_page_items');
      return raw ? JSON.parse(raw) : [];
    } catch { return []; }
  }, []);

  const listCtx = useMemo(() => {
    try {
      const raw = sessionStorage.getItem('zhihu_list_ctx');
      return raw ? JSON.parse(raw) as {
        keyword: string; task_id: string | null; order_by: string; order_direction: string;
        page: string; page_size: number; total: number;
      } : null;
    } catch { return null; }
  }, []);

  // 在当前页 items 中的索引
  const currentIdx = pageItems.indexOf(contentId!);
  const hasCachedPrev = currentIdx > 0;
  const hasCachedNext = currentIdx >= 0 && currentIdx < pageItems.length - 1;

  // ── 计算当前阅读进度位置 ────────────────────────────────────
  const progressInfo = useMemo(() => {
    if (!listCtx) return null;
    const ctxPage = Number(listCtx.page) || 1;
    const ctxPageSize = listCtx.page_size || 20;
    const ctxTotal = listCtx.total || 0;
    const totalPages = Math.max(1, Math.ceil(ctxTotal / ctxPageSize));
    if (currentIdx >= 0) {
      const globalIdx = (ctxPage - 1) * ctxPageSize + currentIdx + 1;
      return { globalIdx, total: ctxTotal, page: ctxPage, totalPages };
    }
    return {
      globalIdx: (ctxPage - 1) * ctxPageSize + 1,
      total: ctxTotal, page: ctxPage, totalPages,
    };
  }, [listCtx, currentIdx]);

  // 跨页邻居查询
  const { data: neighborsData, isFetching: neighborsLoading } = useQuery({
    queryKey: ['zhihu-neighbors', contentId, listCtx],
    queryFn: () => fetchContentNeighbors('zhihu', {
      content_id: contentId!,
      order_by: listCtx?.order_by || undefined,
      order_direction: (listCtx?.order_direction as 'asc' | 'desc') || undefined,
      keyword: listCtx?.keyword || undefined,
      task_id: listCtx?.task_id ? Number(listCtx.task_id) : undefined,
    }),
    enabled: !!contentId,
    staleTime: 0,
  });

  // 确定上一条 / 下一条的 content_id
  const prevContentId = hasCachedPrev ? pageItems[currentIdx - 1] : (neighborsData?.prev?.content_id as string) || null;
  const nextContentId = hasCachedNext ? pageItems[currentIdx + 1] : (neighborsData?.next?.content_id as string) || null;

  // 判断是否在边界
  const isFirst = !prevContentId && !neighborsLoading;
  const isLast = !nextContentId && !neighborsLoading;

  const navigateToItem = useCallback((targetContentId: string) => {
    navigate(`/zhihu/${targetContentId}`);
  }, [navigate]);

  // ── 文本选中添加关键词 ──────────────────────────────────────
  const contentRef = useRef<HTMLDivElement>(null);
  const [selectionPopup, setSelectionPopup] = useState<{
    text: string; x: number; y: number; visible: boolean;
  }>({ text: '', x: 0, y: 0, visible: false });

  useEffect(() => {
    const handleMouseUp = () => {
      setTimeout(() => {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed || !sel.toString().trim()) {
          setSelectionPopup((p) => (p.visible ? { ...p, visible: false } : p));
          return;
        }
        const selectedText = sel.toString().trim();
        if (!selectedText || selectedText.length < 2) {
          setSelectionPopup((p) => (p.visible ? { ...p, visible: false } : p));
          return;
        }
        // 只响应用户在内容区域内的选中
        const container = contentRef.current;
        if (!container) return;
        const range = sel.getRangeAt(0);
        if (!container.contains(range.commonAncestorContainer)) {
          setSelectionPopup((p) => (p.visible ? { ...p, visible: false } : p));
          return;
        }
        const rect = range.getBoundingClientRect();
        setSelectionPopup({
          text: selectedText.length > 30 ? selectedText.slice(0, 30) + '…' : selectedText,
          x: rect.left + rect.width / 2,
          y: rect.top - 12,
          visible: true,
        });
      }, 10);
    };
    const handleMouseDown = (e: MouseEvent) => {
      // 点击弹窗外关闭
      if (selectionPopup.visible) {
        const target = e.target as HTMLElement;
        if (!target.closest('.selection-keyword-popup')) {
          setSelectionPopup((p) => ({ ...p, visible: false }));
        }
      }
    };
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mousedown', handleMouseDown);
    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mousedown', handleMouseDown);
    };
  }, [selectionPopup.visible]);

  const handleAddSelectionKeyword = useCallback(() => {
    if (!selectionPopup.text) return;
    addKeywordsMut.mutate([selectionPopup.text]);
    setSelectionPopup((p) => ({ ...p, visible: false }));
  }, [selectionPopup.text, addKeywordsMut]);

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
            <Button.Group>
              <Tooltip title={isFirst ? '已是第一条' : '上一条'}>
                <Button
                  icon={<LeftOutlined />}
                  disabled={isFirst}
                  loading={!hasCachedPrev && neighborsLoading}
                  onClick={() => prevContentId && navigateToItem(prevContentId)}
                >
                  上一条
                </Button>
              </Tooltip>
              <Tooltip title={isLast ? '已是最后一条' : '下一条'}>
                <Button
                  icon={<RightOutlined />}
                  disabled={isLast}
                  loading={!hasCachedNext && neighborsLoading}
                  onClick={() => nextContentId && navigateToItem(nextContentId)}
                >
                  下一条
                </Button>
              </Tooltip>
            </Button.Group>
            {progressInfo && (
              <Tag color="blue" style={{ fontSize: 12, margin: 0, lineHeight: '22px' }}>
                第 {progressInfo.globalIdx}/{progressInfo.total} 条 · 第 {progressInfo.page}/{progressInfo.totalPages} 页
              </Tag>
            )}
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(returnPath)}>返回</Button>
            {data.content_url && (
              <Button
                icon={<ExportOutlined />}
                onClick={() => window.open(String(data.content_url), '_blank', 'noopener')}
              >
                查看原文
              </Button>
            )}
            <Button
              type="primary"
              icon={<RocketOutlined />}
              loading={crawlCreatorMut.isPending}
              onClick={handleCrawlCreator}
            >
              爬取作者全部信息
            </Button>
            <Button
              icon={<RobotOutlined />}
              loading={analyzeMut.isPending}
              onClick={() => analyzeMut.mutate()}
            >
              AI 分析
            </Button>
          </Space>
        }
      />

      <Card style={{ borderRadius: 12 }}>
        {/* 内容正文区域（文本选中添加关键词的作用域） */}
        <div ref={contentRef}>
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
                maxWidth: '100%', userSelect: 'text',
              }}
              dangerouslySetInnerHTML={{ __html: contentBody }}
            />
          ) : (
            <Typography.Paragraph
              style={{
                fontSize: 15, lineHeight: 1.85, whiteSpace: 'pre-wrap',
                wordBreak: 'break-word', userSelect: 'text',
              }}
            >
              {contentBody || '（无内容）'}
            </Typography.Paragraph>
          )}

          {/* 文本选中弹窗 */}
          {selectionPopup.visible && (
            <div
              className="selection-keyword-popup"
              style={{
                position: 'fixed',
                left: selectionPopup.x,
                top: selectionPopup.y,
                transform: 'translate(-50%, -100%)',
                zIndex: 1050,
                background: '#fff',
                borderRadius: 8,
                boxShadow: '0 6px 20px rgba(0,0,0,0.15)',
                padding: '8px 12px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 13,
                whiteSpace: 'nowrap',
              }}
            >
              <PushpinOutlined style={{ color: '#1677ff', fontSize: 14 }} />
              <span style={{
                maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis',
                color: '#333', fontWeight: 500,
              }}>
                "{selectionPopup.text}"
              </span>
              {addedKeywords.has(selectionPopup.text) ? (
                <Tag color="success" icon={<CheckOutlined />} style={{ margin: 0 }}>已添加</Tag>
              ) : (
                <Button
                  type="primary"
                  size="small"
                  icon={<PlusOutlined />}
                  loading={addKeywordsMut.isPending}
                  onClick={handleAddSelectionKeyword}
                >
                  添加为关键词
                </Button>
              )}
            </div>
          )}
        </div>

        {/* AI 分析结果 */}
        {aiResult && (
          <>
            <Divider style={{ margin: '20px 0' }} />
            <Card
              size="small"
              title={
                <Space>
                  <RobotOutlined />
                  <span>AI 分析总结</span>
                </Space>
              }
              style={{ marginBottom: 16, background: '#fafafa' }}
            >
              <Typography.Paragraph style={{ fontSize: 14, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                {aiResult.summary}
              </Typography.Paragraph>

              <Divider style={{ margin: '12px 0' }} />

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <Typography.Text strong>关键词总结</Typography.Text>
                {aiResult.keywords.some((k) => !addedKeywords.has(k)) && (
                  <Button
                    size="small"
                    type="dashed"
                    icon={<PlusOutlined />}
                    loading={addKeywordsMut.isPending}
                    onClick={handleAddAllKeywords}
                  >
                    全部添加到关键词库
                  </Button>
                )}
              </div>
              <Space wrap size={[8, 8]}>
                {aiResult.keywords.map((kw) => {
                  const added = addedKeywords.has(kw);
                  return (
                    <Tooltip key={kw} title={added ? '已添加' : '点击添加到关键词库'}>
                      <Tag
                        color={added ? 'green' : 'blue'}
                        style={{ cursor: added ? 'default' : 'pointer', fontSize: 13, padding: '2px 8px' }}
                        onClick={() => !added && handleAddKeyword(kw)}
                        closeIcon={!added ? <PlusOutlined /> : undefined}
                      >
                        {kw}
                      </Tag>
                    </Tooltip>
                  );
                })}
              </Space>
            </Card>
          </>
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
