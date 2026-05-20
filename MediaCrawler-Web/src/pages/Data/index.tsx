import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Button,
  Card,
  Image,
  Modal,
  Space,
  Tag,
  Typography,
} from 'antd';
import { BarChartOutlined, DeleteOutlined, EyeOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMemo, useState, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';

import {
  fetchDbData,
  fetchDbPlatforms,
  fetchTaskData,
  fetchContentComments,
  deleteDataRecord,
} from '@/api';
import { analyzeComments, type AnalyzeResponse } from '@/api/modules/ai';
import PageHeader from '@/components/PageHeader';
import { isImageUrl, formatText } from '@/utils/format';
import {
  IMPORTANT_FIELDS,
  FIELD_LABELS,
  IMAGE_FIELDS,
  CONTENT_ID_FIELDS,
  KIND_LABELS,
} from '@/constants';

import DataFilterBar from './components/DataFilterBar';
import DataFilterAlerts from './components/DataFilterAlerts';
import DataTable from './components/DataTable';
import DataDetailModal from './components/DataDetailModal';
import AnalysisResultCard from './AnalysisResultCard';

export default function DataPage() {
  const { message, modal } = App.useApp();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const urlTaskId = searchParams.get('task_id');
  const urlPlatform = searchParams.get('platform') || 'xhs';

  const [platform, setPlatform] = useState(urlPlatform);
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

  const { data: platformMeta } = useQuery({
    queryKey: ['db-platforms'],
    queryFn: fetchDbPlatforms,
  });

  const kinds = useMemo(() => {
    const p = platformMeta?.platforms.find((x) => x.value === platform);
    return p?.kinds ?? [];
  }, [platformMeta, platform]);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['db-data', platform, kind, page, searchKeyword, filterTaskId, filterContentId],
    queryFn: () => {
      if (filterTaskId) {
        return fetchTaskData(platform, Number(filterTaskId), { page, page_size: 20 });
      }
      if (filterContentId && kind === 'comments') {
        return fetchContentComments(platform, filterContentId, { page, page_size: 20 });
      }
      if (filterContentId && kind === 'contents') {
        return fetchDbData(platform, kind, { page, page_size: 20, content_id: filterContentId });
      }
      return fetchDbData(platform, kind, { page, page_size: 20, keyword: searchKeyword || undefined });
    },
    placeholderData: keepPreviousData,
    retry: false,
  });

  const deleteMutation = useMutation({
    mutationFn: (recordId: number) => deleteDataRecord(platform, kind, recordId),
    onSuccess: () => {
      message.success('记录已删除');
      void queryClient.invalidateQueries({ queryKey: ['db-data'] });
    },
  });

  const abortRef = useRef<AbortController | null>(null);

  const handleAnalyzeComments = useCallback(async (contentId: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setAnalyzingContentId(contentId);
    setAnalysisLoading(true);
    try {
      const result = await analyzeComments({ platform, content_id: contentId }, controller.signal);
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
                src={firstUrl}
                width={32}
                height={32}
                style={{ borderRadius: 4, objectFit: 'cover' }}
                preview={{ mask: null }}
                fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHJ4PSIxNiIgZmlsbD0iI0UyRThGMCIvPjwvc3ZnPg=="
              />
            );
          }
          return formatText(field, v);
        }

        if (IMAGE_FIELDS.has(field) && isImageUrl(s)) {
          return (
            <Image
              src={s}
              width={32}
              height={32}
              style={{ borderRadius: 20, objectFit: 'cover' }}
              preview={{ mask: null }}
              fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHJ4PSIxNiIgZmlsbD0iI0UyRThGMCIvPjwvc3ZnPg=="
            />
          );
        }
        return formatText(field, v);
      },
    }));

    const actionCol = {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right' as const,
      render: (_: unknown, r: Record<string, unknown>) => {
        const recordId = r.id as number;
        const cid = r[contentIdField] as string | undefined;

        return (
          <Space size="small">
            {kind === 'contents' && cid && (
              <>
                <Button
                  type="link"
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    setFilterContentId(cid);
                    setKind('comments');
                    setPage(1);
                    setFilterTaskId(null);
                  }}
                >
                  查看评论
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
              </>
            )}
            {kind === 'comments' && cid && (
              <Button
                type="link"
                size="small"
                icon={<SearchOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  setFilterContentId(cid);
                  setFilterTaskId(null);
                  setKind('contents');
                  setSearchKeyword('');
                  setKeyword('');
                  setPage(1);
                }}
              >
                查看原内容
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
                src={url}
                width={80}
                height={80}
                style={{ borderRadius: 8, objectFit: 'cover' }}
                fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iODAiIGhlaWdodD0iODAiIHJ4PSI4IiBmaWxsPSIjRTJFOEYwIi8+PC9zdmc+"
              />
            ))}
          </Space>
        </Image.PreviewGroup>
      );
    }

    if (IMAGE_FIELDS.has(key) && isImageUrl(s)) {
      return <Image src={s} width={80} height={80} style={{ borderRadius: 8, objectFit: 'cover' }} />;
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
          hasFilters={!!(filterTaskId || filterContentId)}
          onPlatformChange={setPlatform}
          onKindChange={setKind}
          onKeywordChange={setKeyword}
          onSearch={handleSearch}
          onClearFilters={handleClearFilters}
        />

        <DataFilterAlerts
          filterTaskId={filterTaskId}
          filterContentId={filterContentId}
          kind={kind}
          platform={platform}
          contentIdField={contentIdField}
          onClear={handleClearFilters}
        />

        <DataTable
          columns={columns}
          dataSource={data?.items ?? []}
          isLoading={isLoading}
          isError={isError}
          error={error as Error | null}
          page={page}
          pageSize={data?.page_size ?? 20}
          total={data?.total ?? 0}
          onPageChange={setPage}
          onRowClick={setDetailRow}
        />

        <DataDetailModal
          detailRow={detailRow}
          allFields={allFields}
          renderValue={renderDetailValue}
          onDelete={handleDeleteDetail}
          onClose={() => setDetailRow(null)}
        />

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
    </>
  );
}
