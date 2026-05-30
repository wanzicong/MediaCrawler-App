import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Button,
  Card,
  FloatButton,
  Image,
  Modal,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import { AppstoreOutlined, BarChartOutlined, CloudDownloadOutlined, DeleteOutlined, ExportOutlined, EyeOutlined, ReadOutlined, SearchOutlined, UnorderedListOutlined, VerticalAlignBottomOutlined, VerticalAlignTopOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMemo, useState, useCallback, useRef, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';

import {
  fetchDbData,
  fetchDbPlatforms,
  fetchTaskData,
  fetchContentComments,
  deleteDataRecord,
  fetchAvailableTasks,
} from '@/api';
import { analyzeComments, type AnalyzeResponse } from '@/api/modules/ai';
import { commentAsync } from '@/api/modules/comments';
import PageHeader from '@/components/PageHeader';
import { isImageUrl, formatText, normalizeImageUrl } from '@/utils/format';
import {
  IMPORTANT_FIELDS,
  FIELD_LABELS,
  IMAGE_FIELDS,
  CONTENT_ID_FIELDS,
  KIND_LABELS,
  PLATFORM_LABELS,
  ZHIHU_CONTENT_TYPE_LABELS,
  getPlatformUrl,
} from '@/constants';
import { fetchEnabledPlatforms } from '@/api/modules/platforms';

import DataFilterBar from './components/DataFilterBar';
import DataFilterAlerts from './components/DataFilterAlerts';
import DataTable from './components/DataTable';
import DataCardView from './components/DataCardView';
import DataDetailModal from './components/DataDetailModal';
import AnalysisResultCard from './AnalysisResultCard';

export default function DataPage() {
  const { message, modal } = App.useApp();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const urlTaskId = searchParams.get('task_id');
  const urlPlatform = searchParams.get('platform'); // URL 参数或 null

  const [platform, setPlatform] = useState(urlPlatform || '');
  const [kind, setKind] = useState('contents');
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [detailRow, setDetailRow] = useState<Record<string, unknown> | null>(null);
  const [filterContentId, setFilterContentId] = useState<string | null>(null);
  const [filterTaskId, setFilterTaskId] = useState<string | null>(urlTaskId);
  const [analyzingContentId, setAnalyzingContentId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResponse | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [commentModalCid, setCommentModalCid] = useState<string | null>(null);
  const [commentModalPage, setCommentModalPage] = useState(1);
  const [orderBy, setOrderBy] = useState('');
  const [orderDirection, setOrderDirection] = useState('desc');
  const [viewMode, setViewMode] = useState<'table' | 'card'>('card');
  const [pageSize, setPageSize] = useState(20);

  // 视频类平台支持的排序字段
  const videoSortOptions = useMemo(() => {
    const fields: Record<string, { value: string; label: string }[]> = {
      bili: [
        { value: 'video_play_count', label: '播放量' },
        { value: 'video_comment', label: '评论数' },
        { value: 'liked_count', label: '点赞数' },
      ],
      dy: [
        { value: 'viewd_count', label: '播放量' },
        { value: 'comment_count', label: '评论数' },
        { value: 'liked_count', label: '点赞数' },
      ],
      ks: [
        { value: 'video_play_count', label: '播放量' },
        { value: 'video_comment', label: '评论数' },
        { value: 'liked_count', label: '点赞数' },
      ],
    };
    return fields[platform] ?? [];
  }, [platform]);

  // 创作者类型支持的排序字段（按粉丝数/关注数）
  const creatorSortOptions = useMemo(() => {
    if (kind !== 'creators') return [];
    return [
      { value: 'fans', label: '粉丝数' },
      { value: 'follows', label: '关注数' },
    ];
  }, [kind]);

  // 切换平台/类型时重置排序
  const handlePlatformChange = useCallback((v: string) => {
    setPlatform(v);
    setOrderBy('');
    setOrderDirection('desc');
    setPage(1);
  }, []);

  const handleKindChange = useCallback((v: string) => {
    setKind(v);
    if (v === 'creators') {
      setOrderBy('fans');
      setOrderDirection('desc');
    } else {
      setOrderBy('');
      setOrderDirection('desc');
    }
    setPage(1);
  }, []);

  const { data: platformMeta } = useQuery({
    queryKey: ['db-platforms'],
    queryFn: fetchDbPlatforms,
  });

  const { data: enabledPlatforms } = useQuery({
    queryKey: ['platforms', 'enabled'],
    queryFn: fetchEnabledPlatforms,
    staleTime: 5 * 60 * 1000,
  });

  // 无 URL 参数时，默认选中第一个启用的平台
  useEffect(() => {
    if (!urlPlatform && enabledPlatforms && enabledPlatforms.length > 0 && !platform) {
      setPlatform(enabledPlatforms[0].code);
    }
  }, [urlPlatform, enabledPlatforms, platform]);

  // 评论弹窗数据
  const { data: commentModalData, isLoading: commentModalLoading } = useQuery({
    queryKey: ['content-comments', platform, commentModalCid, commentModalPage],
    queryFn: () => fetchContentComments(platform, commentModalCid!, { page: commentModalPage, page_size: 20 }),
    enabled: !!commentModalCid,
    placeholderData: keepPreviousData,
  });

  const kinds = useMemo(() => {
    const p = platformMeta?.platforms.find((x) => x.value === platform);
    return p?.kinds ?? [];
  }, [platformMeta, platform]);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['db-data', platform, kind, page, pageSize, searchKeyword, filterTaskId, filterContentId, orderBy, orderDirection],
    queryFn: () => {
      if (filterTaskId) {
        return fetchTaskData(platform, Number(filterTaskId), { page, page_size: pageSize, order_by: orderBy || undefined, order_direction: orderDirection });
      }
      if (filterContentId && kind === 'comments') {
        return fetchContentComments(platform, filterContentId, { page, page_size: pageSize });
      }
      if (filterContentId && kind === 'contents') {
        return fetchDbData(platform, kind, { page, page_size: pageSize, content_id: filterContentId, order_by: orderBy || undefined, order_direction: orderDirection });
      }
      return fetchDbData(platform, kind, { page, page_size: pageSize, keyword: searchKeyword || undefined, order_by: orderBy || undefined, order_direction: orderDirection });
    },
    placeholderData: keepPreviousData,
    retry: false,
    enabled: !!platform,
  });

  // 获取当前视图中有数据的任务列表（用于任务筛选下拉框）
  const { data: availableTasks = [], isLoading: tasksLoading } = useQuery({
    queryKey: ['available-tasks', platform, kind],
    queryFn: () => fetchAvailableTasks(platform, kind),
    staleTime: 30 * 1000,
    enabled: !!platform,
  });

  const deleteMutation = useMutation({
    mutationFn: (recordId: number) => deleteDataRecord(platform, kind, recordId),
    onSuccess: () => {
      message.success('记录已删除');
      void queryClient.invalidateQueries({ queryKey: ['db-data'] });
    },
  });

  const crawlCommentMutation = useMutation({
    mutationFn: (postId: string) =>
      commentAsync({ platform, post_id: postId, max_comments: 50, crawl_replies: false }),
    onSuccess: (res) => {
      message.success(`评论爬取任务已提交 (ID: ${res.task_id})`);
    },
  });

  const handleCrawlComments = useCallback((cid: string) => {
    crawlCommentMutation.mutate(cid);
  }, [crawlCommentMutation]);

  const abortRef = useRef<AbortController | null>(null);

  const handleAnalyzeComments = useCallback(async (contentId: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setAnalyzingContentId(contentId);
    setAnalysisLoading(true);
    try {
      const result = await analyzeComments({ platform, content_id: String(contentId) }, controller.signal);
      if (!controller.signal.aborted) {
        setAnalysisResult(result);
      }
    } catch {
      if (!controller.signal.aborted) {
        // 全局请求拦截器已显示错误提示
      }
    } finally {
      if (!controller.signal.aborted) {
        setAnalysisLoading(false);
      }
    }
  }, [platform]);

  const importantFields = useMemo(() => {
    const key = `${platform}.${kind}`;
    return IMPORTANT_FIELDS[key] ?? [];
  }, [platform, kind]);

  const contentIdField = useMemo(() => CONTENT_ID_FIELDS[platform] || 'note_id', [platform]);

  const columns: ColumnsType<Record<string, unknown>> = useMemo(() => {
    const dataCols = importantFields.map((field) => ({
      title: FIELD_LABELS[field] || field,
      dataIndex: field,
      key: field,
      ellipsis: !IMAGE_FIELDS.has(field) ? { tooltip: { placement: 'top', mouseEnterDelay: 0.3 } } : false,
      width:
        field === 'id' || field === 'comment_id' || field === 'note_id' || field === 'video_id' || field === 'aweme_id' || field === 'content_id'
          ? 100
          : IMAGE_FIELDS.has(field)
            ? 56
            : field === 'title' || field === 'content' || field === 'desc' || field === 'content_text'
              ? 200
              : undefined,
      render: (v: unknown) => {
        if (v == null) return '—';
        const s = String(v);

        // image_list 是逗号分隔的 URL 列表，取第一张作为封面
        if (field === 'image_list') {
          const firstUrl = s.split(',')[0].trim();
          if (firstUrl && isImageUrl(firstUrl)) {
            return (
              <Image
                src={normalizeImageUrl(firstUrl)}
                width={32}
                height={32}
                style={{ borderRadius: 4, objectFit: 'cover' }}
                preview={{ mask: null }}
                referrerPolicy="no-referrer"
                fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHJ4PSIxNiIgZmlsbD0iI0UyRThGMCIvPjwvc3ZnPg=="
              />
            );
          }
          return formatText(field, v);
        }

        if (IMAGE_FIELDS.has(field) && isImageUrl(s)) {
          return (
            <Image
              src={normalizeImageUrl(s)}
              width={32}
              height={32}
              style={{ borderRadius: 20, objectFit: 'cover' }}
              preview={{ mask: null }}
              referrerPolicy="no-referrer"
              fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHJ4PSIxNiIgZmlsbD0iI0UyRThGMCIvPjwvc3ZnPg=="
            />
          );
        }
        if (field === 'content_type') {
          const typeInfo = ZHIHU_CONTENT_TYPE_LABELS[s] || { label: s, color: 'default' };
          return <Tag color={typeInfo.color}>{typeInfo.label}</Tag>;
        }
        return formatText(field, v);
      },
    }));

    const actionCol = {
      title: '操作',
      key: 'action',
      width: 240,
      fixed: 'right' as const,
      render: (_: unknown, r: Record<string, unknown>) => {
        const recordId = r.id as number;
        const cid = r[contentIdField] as string | undefined;
        const platformUrl = getPlatformUrl(platform, r);
        const platformName = PLATFORM_LABELS[platform] || '平台';

        return (
          <Space size="small" wrap>
            {platformUrl && (
              <Button
                type="link"
                size="small"
                icon={<ExportOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(platformUrl, '_blank', 'noopener');
                }}
              >
                {platformName}
              </Button>
            )}
            {kind === 'contents' && cid && (
              <>
                <Button
                  type="link"
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    setCommentModalCid(cid);
                    setCommentModalPage(1);
                  }}
                >
                  评论
                </Button>
                <Button
                  type="link"
                  size="small"
                  icon={<BarChartOutlined />}
                  loading={analyzingContentId === cid && analysisLoading}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAnalyzeComments(cid);
                  }}
                >
                  AI 分析
                </Button>
                <Button
                  type="link"
                  size="small"
                  icon={<CloudDownloadOutlined />}
                  loading={crawlCommentMutation.isPending}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCrawlComments(cid);
                  }}
                >
                  爬取评论
                </Button>
              </>
            )}
            {platform === 'zhihu' && kind === 'contents' && cid && (
              <Button
                type="link"
                size="small"
                icon={<ReadOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/zhihu/${cid}`);
                }}
              >
                查看全文
              </Button>
            )}
            <Button
              type="link"
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                modal.confirm({
                  title: '确认删除',
                  content: `确定要删除这条${KIND_LABELS[kind] || '数据'}吗？此操作不可恢复。`,
                  okText: '删除',
                  okType: 'danger',
                  cancelText: '取消',
                  onOk: () => deleteMutation.mutate(recordId),
                });
              }}
            />
          </Space>
        );
      },
    };

    return [...dataCols, actionCol];
  }, [importantFields, platform, kind, contentIdField, deleteMutation, modal, analyzingContentId, analysisLoading, handleAnalyzeComments]);

  const allFields = useMemo(() => {
    if (!detailRow) return [];
    return Object.keys(detailRow).map((key) => ({
      key,
      label: FIELD_LABELS[key] || key,
      value: detailRow[key],
    }));
  }, [detailRow]);

  const renderDetailValue = (key: string, v: unknown) => {
    if (v == null) return '—';
    const s = String(v);

   if (key === 'image_list') {
      const urls = s.split(',').map(u => u.trim()).filter(isImageUrl);
      if (urls.length === 0) return formatText(key, v);
      return (
        <Image.PreviewGroup>
          <Space wrap size={4}>
            {urls.map((url, i) => (
              <Image
                key={i}
                src={normalizeImageUrl(url)}
                width={80}
                height={80}
                style={{ borderRadius: 8, objectFit: 'cover' }}
                referrerPolicy="no-referrer"
                fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iODAiIGhlaWdodD0iODAiIHJ4PSI4IiBmaWxsPSIjRTJFOEYwIi8+PC9zdmc+"
              />
            ))}
          </Space>
        </Image.PreviewGroup>
      );
    }

    if (IMAGE_FIELDS.has(key) && isImageUrl(s)) {
      return <Image src={normalizeImageUrl(s)} width={80} height={80} style={{ borderRadius: 8, objectFit: 'cover' }} referrerPolicy="no-referrer" />;
    }
    if (isImageUrl(s)) {
      return (
        <Typography.Link href={s} target="_blank" rel="noopener noreferrer" copyable>
          {s.length > 60 ? `${s.slice(0, 60)}…` : s}
        </Typography.Link>
      );
    }
    return formatText(key, v);
  };

  const handleSearch = useCallback((v: string) => {
    setSearchKeyword(v);
    setPage(1);
  }, []);

  const handleTaskIdChange = useCallback((v: string | null) => {
    setFilterTaskId(v);
    setFilterContentId(null);
    setSearchKeyword('');
    setKeyword('');
    setPage(1);
  }, []);

  const handleClearFilters = useCallback(() => {
    setFilterTaskId(null);
    setFilterContentId(null);
    setSearchKeyword('');
    setKeyword('');
    setPage(1);
    setSearchParams({});
  }, [setSearchParams]);

  const handleDeleteDetail = (recordId: number) => {
    modal.confirm({
      title: '确认删除',
      content: '确定要删除这条记录吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        deleteMutation.mutate(recordId);
        setDetailRow(null);
      },
    });
  };

  return (
    <>
      <PageHeader
        title="数据中心"
        description="从 MySQL 查询已爬取的结构化数据，支持任务关联、内容评论联动和删除"
      />
      <Card>
        <DataFilterBar
          platform={platform}
          platforms={platformMeta?.platforms ?? []}
          kind={kind}
          kinds={kinds}
          keyword={keyword}
          dataTotal={data?.total}
          hasFilters={!!(filterTaskId || filterContentId || searchKeyword)}
          sortOptions={[...videoSortOptions, ...creatorSortOptions]}
          orderBy={orderBy}
          orderDirection={orderDirection}
          filterTaskId={filterTaskId}
          availableTasks={availableTasks}
          tasksLoading={tasksLoading}
          onPlatformChange={handlePlatformChange}
          onKindChange={handleKindChange}
          onKeywordChange={setKeyword}
          onSearch={handleSearch}
          onClearFilters={handleClearFilters}
          onOrderByChange={setOrderBy}
          onOrderDirectionChange={setOrderDirection}
          onTaskIdChange={handleTaskIdChange}
        />

        <DataFilterAlerts
          filterTaskId={filterTaskId}
          filterContentId={filterContentId}
          kind={kind}
          platform={platform}
          contentIdField={contentIdField}
          platforms={enabledPlatforms}
          onClear={handleClearFilters}
        />

        <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'flex-end' }}>
          <Button.Group>
            <Button
              type={viewMode === 'table' ? 'primary' : 'default'}
              icon={<UnorderedListOutlined />}
              onClick={() => setViewMode('table')}
            >
              列表
            </Button>
            <Button
              type={viewMode === 'card' ? 'primary' : 'default'}
              icon={<AppstoreOutlined />}
              onClick={() => setViewMode('card')}
            >
              卡片
            </Button>
          </Button.Group>
        </div>

        {viewMode === 'table' ? (
          <DataTable
            columns={columns}
            dataSource={data?.items ?? []}
            isLoading={isLoading}
            isError={isError}
            error={error as Error | null}
            page={page}
            pageSize={data?.page_size ?? pageSize}
            total={data?.total ?? 0}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            onRowClick={setDetailRow}
          />
        ) : (
          <DataCardView
            dataSource={data?.items ?? []}
            isLoading={isLoading}
            isError={isError}
            error={error as Error | null}
            platform={platform}
            kind={kind}
            page={page}
            pageSize={data?.page_size ?? pageSize}
            total={data?.total ?? 0}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            onCardClick={setDetailRow}
            onViewComments={(cid) => {
              setCommentModalCid(cid);
              setCommentModalPage(1);
            }}
            onCrawlComments={handleCrawlComments}
            crawlPending={crawlCommentMutation.isPending}
          />
        )}

        <DataDetailModal
          detailRow={detailRow}
          allFields={allFields}
          renderValue={renderDetailValue}
          onDelete={handleDeleteDetail}
          onClose={() => setDetailRow(null)}
          platform={platform}
        />

        <Modal
          title={
            <Space>
              <EyeOutlined />
              <span>评论列表</span>
              {commentModalData && (
                <Tag>{commentModalData.total} 条评论</Tag>
              )}
            </Space>
          }
          open={!!commentModalCid}
          onCancel={() => setCommentModalCid(null)}
          footer={null}
          width={800}
        >
          <Table
            rowKey="id"
            loading={commentModalLoading}
            dataSource={commentModalData?.items ?? []}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 60 },
              { title: '评论内容', dataIndex: 'content', ellipsis: true, render: (v: unknown) => v ? String(v) : '—' },
              {
                title: '点赞',
                dataIndex: 'like_count',
                width: 80,
                render: (v: unknown) => v ?? '—',
              },
              {
                title: '时间',
                dataIndex: 'create_time',
                width: 160,
                render: (v: unknown) => v ? formatText('create_time', v) : '—',
              },
            ]}
            pagination={{
              current: commentModalPage,
              pageSize: 20,
              total: commentModalData?.total ?? 0,
              onChange: setCommentModalPage,
              showTotal: (t) => `共 ${t} 条`,
            }}
            size="small"
            scroll={{ y: 400 }}
          />
        </Modal>

        <Modal
          title={
            <Space>
              <BarChartOutlined style={{ color: '#6366f1' }} />
              <span>AI 评论分析</span>
              {analysisResult && (
                <Tag color="purple">{analysisResult.comment_count} 条评论</Tag>
              )}
            </Space>
          }
          open={!!analysisResult}
          onCancel={() => setAnalysisResult(null)}
          footer={null}
          width={720}
        >
          {analysisResult && <AnalysisResultCard result={analysisResult} />}
        </Modal>
      </Card>

      <FloatButton.Group>
        <FloatButton
          icon={<VerticalAlignTopOutlined />}
          tooltip="回到顶部"
          onClick={() => {
            document.getElementById('page-scroll-container')?.scrollTo({ top: 0, behavior: 'smooth' });
          }}
        />
        <FloatButton
          icon={<VerticalAlignBottomOutlined />}
          tooltip="回到底部"
          onClick={() => {
            const el = document.getElementById('page-scroll-container');
            if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
          }}
        />
      </FloatButton.Group>
    </>
  );
}
