import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Button,
  Card,
  Checkbox,
  ColorPicker,
  Empty,
  Form,
  Input,
  Modal,
  Pagination,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  ExperimentOutlined,
  PlusOutlined,
  ReloadOutlined,
  RocketOutlined,
  StarOutlined,
  TagOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  fetchKeywordGroups,
  createKeywordGroup,
  updateKeywordGroup,
  deleteKeywordGroup,
  fetchKeywords,
  createKeyword,
  batchCreateKeywords,
  updateKeyword,
  deleteKeyword,
  batchDeleteKeywords,
  fissionKeywords,
  fetchKeywordStats,
  runKeyword,
  autoClassifyKeyword,
  batchAutoClassify,
  reclassifyAllKeywords,
  type Keyword,
  type KeywordGroup,
  type FissionResult,
  type KeywordStats,
} from '@/api/modules/keywords';
import PageHeader from '@/components/PageHeader';
import { PLATFORM_LABELS, KIND_LABELS } from '@/constants';
import { fetchEnabledPlatforms } from '@/api/modules/platforms';

import styles from './index.module.less';

const { Text, Paragraph, Title } = Typography;

const SOURCE_LABELS: Record<string, string> = { manual: '手动', fission: '裂变', ai: 'AI' };
const SOURCE_COLORS: Record<string, string> = { manual: 'blue', fission: 'green', ai: 'purple' };
const STATUS_CFG: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '待爬取' },
  crawled: { color: 'processing', label: '已爬取' },
  has_results: { color: 'green', label: '有结果' },
  no_results: { color: 'red', label: '无结果' },
};

export default function KeywordsPage() {
  const { message, modal } = App.useApp();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [selectedGroup, setSelectedGroup] = useState<number | null>(null);
  const [expandedParents, setExpandedParents] = useState<Set<number>>(new Set());
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [platformFilter, setPlatformFilter] = useState<string | undefined>();
  const [keywordSearch, setKeywordSearch] = useState('');
  const keywordTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<KeywordGroup | null>(null);
  const [keywordModalOpen, setKeywordModalOpen] = useState(false);
  const [editingKeyword, setEditingKeyword] = useState<Keyword | null>(null);
  const [batchKeywordModalOpen, setBatchKeywordModalOpen] = useState(false);

  // Fission state
  const [fissionSeed, setFissionSeed] = useState('');
  const [fissionPlatforms, setFissionPlatforms] = useState<string[]>([]);
  const [fissionDepth, setFissionDepth] = useState(1);
  const [fissionResult, setFissionResult] = useState<FissionResult | null>(null);
  const [fissionLoading, setFissionLoading] = useState(false);
  const [selectedFissionKeys, setSelectedFissionKeys] = useState<string[]>([]);
  const [fissionTargetGroup, setFissionTargetGroup] = useState<number | undefined>();

  const [form] = Form.useForm();
  const [batchForm] = Form.useForm();
  const [groupForm] = Form.useForm();

  // ── Queries ────────────────────────────────────────────────────────

  const { data: groups, isLoading: groupsLoading } = useQuery({
    queryKey: ['keyword-groups'],
    queryFn: fetchKeywordGroups,
  });

  const { data: kwData, isLoading: kwLoading } = useQuery({
    queryKey: ['keywords', selectedGroup, page, statusFilter, platformFilter, keywordSearch],
    queryFn: () =>
      fetchKeywords({
        group_id: selectedGroup ?? undefined,
        page,
        page_size: 50,
        status: statusFilter || undefined,
        platform: platformFilter || undefined,
        keyword: keywordSearch || undefined,
      }),
    placeholderData: (prev) => prev,
  });

  const { data: stats } = useQuery({
    queryKey: ['keyword-stats'],
    queryFn: fetchKeywordStats,
  });

  const { data: platforms } = useQuery({
    queryKey: ['platforms', 'enabled'],
    queryFn: fetchEnabledPlatforms,
    staleTime: 5 * 60 * 1000,
  });

  const getPlatformName = useCallback(
    (code: string) =>
      platforms?.find((p) => p.code === code)?.name || PLATFORM_LABELS[code] || code,
    [platforms],
  );

  const platformOptions = (platforms ?? []).length > 0
    ? platforms!.map((p) => ({ value: p.code, label: p.name }))
    : Object.entries(PLATFORM_LABELS).map(([k, v]) => ({ value: k, label: v }));

  // 第一个启用的平台，作为默认选择
  const defaultPlatform = platforms?.[0]?.code || 'dy';
  const defaultPlatformName = getPlatformName(defaultPlatform);

  // 裂变平台默认同步为第一个启用的平台
  useEffect(() => {
    if (platforms && platforms.length > 0 && fissionPlatforms.length === 0) {
      setFissionPlatforms([platforms[0].code]);
    }
  }, [platforms, fissionPlatforms.length]);

  // ── Group Mutations ─────────────────────────────────────────────────

  const createGroupMut = useMutation({
    mutationFn: (data: Partial<KeywordGroup>) => createKeywordGroup(data),
    onSuccess: () => {
      message.success('分组已创建');
      setGroupModalOpen(false);
      groupForm.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
    },
  });

  const updateGroupMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<KeywordGroup> }) =>
      updateKeywordGroup(id, data),
    onSuccess: () => {
      message.success('分组已更新');
      setGroupModalOpen(false);
      setEditingGroup(null);
      groupForm.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
    },
  });

  const deleteGroupMut = useMutation({
    mutationFn: (id: number) => deleteKeywordGroup(id),
    onSuccess: () => {
      message.success('分组已删除');
      if (selectedGroup === editingGroup?.id) setSelectedGroup(null);
      void queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
      void queryClient.invalidateQueries({ queryKey: ['keywords'] });
    },
  });

  // ── Keyword Mutations ──────────────────────────────────────────────

  const createKwMut = useMutation({
    mutationFn: (data: Partial<Keyword>) => createKeyword(data),
    onSuccess: () => {
      message.success('关键词已添加');
      setKeywordModalOpen(false);
      setEditingKeyword(null);
      form.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['keywords'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-stats'] });
    },
  });

  const updateKwMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Keyword> }) =>
      updateKeyword(id, data),
    onSuccess: () => {
      message.success('关键词已更新');
      setKeywordModalOpen(false);
      setEditingKeyword(null);
      form.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['keywords'] });
    },
  });

  const batchCreateMut = useMutation({
    mutationFn: (data: { keywords: Array<{ keyword: string; notes?: string }>; group_id?: number; platform?: string }) =>
      batchCreateKeywords(data),
    onSuccess: (res) => {
      message.success(`已添加 ${res.length} 个关键词`);
      setBatchKeywordModalOpen(false);
      batchForm.resetFields();
      void queryClient.invalidateQueries({ queryKey: ['keywords'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-stats'] });
    },
  });

  const deleteKwMut = useMutation({
    mutationFn: (id: number) => deleteKeyword(id),
    onSuccess: () => {
      message.success('关键词已删除');
      void queryClient.invalidateQueries({ queryKey: ['keywords'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-stats'] });
    },
  });

  const batchDeleteMut = useMutation({
    mutationFn: (ids: number[]) => batchDeleteKeywords(ids),
    onSuccess: (res) => {
      message.success(`已删除 ${res.deleted_count} 个关键词`);
      setSelectedRowKeys([]);
      void queryClient.invalidateQueries({ queryKey: ['keywords'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-stats'] });
    },
  });

  const runKwMut = useMutation({
    mutationFn: (keywordId: number) => runKeyword(keywordId),
    onSuccess: (res) => {
      message.success(`爬虫任务已启动，任务ID: ${res.task_id}`);
      void queryClient.invalidateQueries({ queryKey: ['keywords'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-stats'] });
    },
  });

  const batchAutoClassifyMut = useMutation({
    mutationFn: (keywordIds: number[]) => batchAutoClassify(keywordIds),
    onSuccess: (res) => {
      message.success(`AI 分类完成，共分类 ${res.classified} 个关键词`);
      void queryClient.invalidateQueries({ queryKey: ['keywords'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-stats'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
    },
  });

  const reclassifyAllMut = useMutation({
    mutationFn: () => reclassifyAllKeywords(),
    onSuccess: (res) => {
      modal.success({
        title: '全部重新分类完成',
        content: (
          <Space direction="vertical" size={6}>
            <Text>处理关键词：<Text strong>{res.processed}</Text> 个</Text>
            <Text>新建分组：<Text strong style={{ color: '#52c41a' }}>{res.groups_created}</Text> 个</Text>
            <Text>重新分配：<Text strong style={{ color: '#1677ff' }}>{res.keywords_reassigned}</Text> 个</Text>
          </Space>
        ),
        width: 360,
      });
      void queryClient.invalidateQueries({ queryKey: ['keywords'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-stats'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
    },
  });

  const classifySingleMut = useMutation({
    mutationFn: (keywordId: number) => autoClassifyKeyword(keywordId),
    onSuccess: (res) => {
      message.success(`「${res.keyword}」已分类至「${res.group_name}」`);
      void queryClient.invalidateQueries({ queryKey: ['keywords'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-stats'] });
      void queryClient.invalidateQueries({ queryKey: ['keyword-groups'] });
    },
  });

  // ── Table Columns ──────────────────────────────────────────────────

  const columns = useMemo(() => {
    const cols = [
      { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
      {
        title: '关键词',
        dataIndex: 'keyword',
        key: 'keyword',
        ellipsis: true,
        render: (v: string) => <Text strong>{v}</Text>,
      },
      {
        title: '平台',
        dataIndex: 'platform',
        key: 'platform',
        width: 80,
        render: (v: string) => (
          <Tag>{getPlatformName(v)}</Tag>
        ),
      },
      {
        title: '分组',
        dataIndex: 'group_id',
        key: 'group_id',
        width: 120,
        render: (v: number | null) => {
          if (v == null) return '—';
          const g = groups?.find((x) => x.id === v);
          return g ? (
            <Space size={4}>
              <span
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: g.color,
                }}
              />
              <span>{g.name}</span>
            </Space>
          ) : '—';
        },
      },
      {
        title: '来源',
        dataIndex: 'source',
        key: 'source',
        width: 70,
        render: (v: string) => (
          <Tag color={SOURCE_COLORS[v] || 'default'}>{SOURCE_LABELS[v] || v}</Tag>
        ),
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        width: 80,
        render: (v: string) => {
          const cfg = STATUS_CFG[v] || { color: 'default', label: v };
          return <Tag color={cfg.color}>{cfg.label}</Tag>;
        },
      },
      {
        title: '操作',
        key: 'action',
        width: 180,
        render: (_: unknown, r: Keyword) => (
          <Space size="small">
            <Button
              type="link"
              size="small"
              icon={<RocketOutlined />}
              onClick={() => {
                modal.confirm({
                  title: '启动爬虫',
                  content: `确认对关键词「${r.keyword}」启动爬虫任务？`,
                  okText: '启动',
                  cancelText: '取消',
                  onOk: () => runKwMut.mutate(r.id),
                });
              }}
            />
            {r.group_id === null && (
              <Button
                type="link"
                size="small"
                icon={<ThunderboltOutlined />}
                loading={classifySingleMut.isPending && classifySingleMut.variables === r.id}
                onClick={() => classifySingleMut.mutate(r.id)}
              />
            )}
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingKeyword(r);
                form.setFieldsValue(r);
                setKeywordModalOpen(true);
              }}
            />
            <Button
              type="link"
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={() => {
                modal.confirm({
                  title: '确认删除',
                  content: `确定要删除关键词「${r.keyword}」吗？`,
                  okText: '删除',
                  okType: 'danger',
                  cancelText: '取消',
                  onOk: () => deleteKwMut.mutate(r.id),
                });
              }}
            />
          </Space>
        ),
      },
    ];
    return cols;
  }, [groups, form, modal, deleteKwMut, runKwMut, getPlatformName]);

  // ── Fission handlers ───────────────────────────────────────────────

  const handleFission = async () => {
    if (!fissionSeed.trim() || fissionPlatforms.length === 0) return;
    setFissionLoading(true);
    try {
      const result = await fissionKeywords({
        seed_keyword: fissionSeed.trim(),
        platforms: fissionPlatforms,
        depth: fissionDepth,
      });
      setFissionResult(result);
      setSelectedFissionKeys(result.generated.map((g) => g.keyword));
    } catch {
      // error toast handled by interceptor
    } finally {
      setFissionLoading(false);
    }
  };

  const handleAcceptFission = async () => {
    if (selectedFissionKeys.length === 0 || !fissionResult) return;
    const selected = fissionResult.generated.filter((g) =>
      selectedFissionKeys.includes(g.keyword),
    );
    // 按平台分组批量创建
    const platformGroups: Record<string, string[]> = {};
    selected.forEach((g) => {
      const p = g.platform || fissionPlatforms[0] || 'xhs';
      if (!platformGroups[p]) platformGroups[p] = [];
      platformGroups[p].push(g.keyword);
    });

    let totalAdded = 0;
    for (const [platform, keywords] of Object.entries(platformGroups)) {
      try {
        const res = await batchCreateKeywords({
          keywords,
          group_id: fissionTargetGroup,
          platform,
        });
        totalAdded += res.length;
      } catch {
        // individual platform failure shouldn't block others
      }
    }

    message.success(`已添加 ${totalAdded} 个裂变关键词到词库`);
    setFissionResult(null);
    setFissionSeed('');
    setFissionPlatforms([]);
    void queryClient.invalidateQueries({ queryKey: ['keywords'] });
    void queryClient.invalidateQueries({ queryKey: ['keyword-stats'] });
  };

  // ── Group context menu ─────────────────────────────────────────────

  const handleEditGroup = (g: KeywordGroup) => {
    setEditingGroup(g);
    groupForm.setFieldsValue(g);
    setGroupModalOpen(true);
  };

  const handleDeleteGroup = (g: KeywordGroup) => {
    const hasChildren = g.children && g.children.length > 0;
    modal.confirm({
      title: '确认删除',
      content: hasChildren
        ? `分组「${g.name}」及其 ${g.children.length} 个子分组和所有关键词都会被删除，确定继续吗？`
        : `分组「${g.name}」下的所有关键词也会被删除，确定继续吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => deleteGroupMut.mutate(g.id),
    });
  };

  // ── Tab 1: Library ─────────────────────────────────────────────────

  const libraryTab = (
    <div className={styles.libraryLayout}>
      {/* Group Sidebar */}
      <div className={styles.groupSidebar}>
        <div className={styles.groupSidebarHeader}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Text strong style={{ fontSize: 13 }}>分组</Text>
            <Button
              type="primary"
              size="small"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingGroup(null);
                groupForm.resetFields();
                setGroupModalOpen(true);
              }}
            />
          </Space>
        </div>
        <div className={styles.groupList}>
          <div
            className={`${styles.groupItem} ${selectedGroup === null && !selectedRowKeys.length ? styles.groupItemActive : ''}`}
            onClick={() => { setSelectedGroup(null); setPage(1); }}
          >
            <span className={styles.groupName}>全部</span>
            <span className={styles.groupCount}>{stats?.total_keywords ?? 0}</span>
          </div>
          <div
            className={`${styles.groupItem} ${selectedGroup === -1 ? styles.groupItemActive : ''}`}
            onClick={() => { setSelectedGroup(-1); setPage(1); }}
            style={{ borderLeft: selectedGroup === -1 ? undefined : '2px solid transparent' }}
          >
            <span className={styles.groupName} style={{ color: '#fa8c16' }}>未分类</span>
            <span className={styles.groupCount}>{stats?.ungrouped_count ?? 0}</span>
          </div>
          {/* Tree groups */}
          {(groups ?? []).map((g) => {
            const hasChildren = g.children && g.children.length > 0;
            const isExpanded = expandedParents.has(g.id);
            return (
              <div key={g.id}>
                <div
                  className={`${styles.groupItem} ${selectedGroup === g.id ? styles.groupItemActive : ''}`}
                  onClick={() => { setSelectedGroup(g.id); setPage(1); }}
                >
                  <span
                    style={{ cursor: 'pointer', width: 14, fontSize: 10, flexShrink: 0, textAlign: 'center' }}
                    onClick={hasChildren ? (e) => {
                      e.stopPropagation();
                      setExpandedParents((prev) => {
                        const next = new Set(prev);
                        if (next.has(g.id)) next.delete(g.id); else next.add(g.id);
                        return next;
                      });
                    } : undefined}
                  >
                    {hasChildren ? (isExpanded ? '▼' : '▶') : ''}
                  </span>
                  <span className={styles.groupColorDot} style={{ background: g.color }} />
                  <span className={styles.groupName}>{g.name}</span>
                  <span className={styles.groupCount}>{g.keyword_count ?? 0}</span>
                  <Button
                    type="text"
                    size="small"
                    icon={<EditOutlined style={{ fontSize: 11 }} />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEditGroup(g);
                    }}
                  />
                  <Button
                    type="text"
                    size="small"
                    danger
                    icon={<DeleteOutlined style={{ fontSize: 11 }} />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteGroup(g);
                    }}
                  />
                </div>
                {/* Sub-groups */}
                {hasChildren && isExpanded && g.children.map((child) => (
                  <div
                    key={child.id}
                    className={`${styles.groupItem} ${selectedGroup === child.id ? styles.groupItemActive : ''}`}
                    style={{ paddingLeft: 40 }}
                    onClick={() => { setSelectedGroup(child.id); setPage(1); }}
                  >
                    <span style={{ width: 14, flexShrink: 0 }} />
                    <span className={styles.groupColorDot} style={{ background: child.color }} />
                    <span className={styles.groupName}>{child.name}</span>
                    <span className={styles.groupCount}>{child.keyword_count ?? 0}</span>
                    <Button
                      type="text"
                      size="small"
                      icon={<EditOutlined style={{ fontSize: 11 }} />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditGroup(child);
                      }}
                    />
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined style={{ fontSize: 11 }} />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteGroup(child);
                      }}
                    />
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>

      {/* Keyword Table Area */}
      <div className={styles.keywordTableArea}>
        <div className={styles.toolbar}>
          <div className={styles.toolbarLeft}>
            <Input.Search
              placeholder="搜索关键词…"
              allowClear
              style={{ width: 200 }}
              defaultValue={keywordSearch}
              onChange={(e) => {
                const v = e.target.value;
                setPage(1);
                if (keywordTimerRef.current) clearTimeout(keywordTimerRef.current);
                keywordTimerRef.current = setTimeout(() => {
                  setKeywordSearch(v);
                }, 300);
              }}
              onSearch={(v) => {
                if (keywordTimerRef.current) clearTimeout(keywordTimerRef.current);
                setKeywordSearch(v);
                setPage(1);
              }}
            />
            <Select
              placeholder="平台筛选"
              allowClear
              style={{ width: 120 }}
              value={platformFilter}
              onChange={(v) => {
                setPlatformFilter(v);
                setPage(1);
              }}
              options={platformOptions}
            />
            <Select
              placeholder="状态筛选"
              allowClear
              style={{ width: 110 }}
              value={statusFilter}
              onChange={(v) => {
                setStatusFilter(v);
                setPage(1);
              }}
              options={[
                { value: 'pending', label: '待爬取' },
                { value: 'crawled', label: '已爬取' },
                { value: 'has_results', label: '有结果' },
                { value: 'no_results', label: '无结果' },
              ]}
            />
          </div>
          <div className={styles.toolbarRight}>
            <Button
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingKeyword(null);
                form.resetFields();
                form.setFieldsValue({ platform: defaultPlatform, group_id: selectedGroup });
                setKeywordModalOpen(true);
              }}
            >
              添加
            </Button>
            <Button
              onClick={() => {
                batchForm.resetFields();
                batchForm.setFieldsValue({ platform: defaultPlatform, group_id: selectedGroup });
                setBatchKeywordModalOpen(true);
              }}
            >
              批量添加
            </Button>
            <Button
              icon={<TagOutlined />}
              loading={batchAutoClassifyMut.isPending}
              onClick={() => {
                const ungroupedIds = (kwData?.items ?? [])
                  .filter((k) => k.group_id === null)
                  .map((k) => k.id);
                if (ungroupedIds.length === 0) {
                  message.info('没有需要分类的未分组关键词');
                  return;
                }
                modal.confirm({
                  title: 'AI 自动分类',
                  content: `将对 ${ungroupedIds.length} 个未分组关键词进行 AI 自动分类，确认继续？`,
                  okText: '开始分类',
                  cancelText: '取消',
                  onOk: () => batchAutoClassifyMut.mutate(ungroupedIds),
                });
              }}
            >
              AI 分类
            </Button>
            <Button
              icon={<ReloadOutlined />}
              danger
              loading={reclassifyAllMut.isPending}
              onClick={() => {
                const totalCount = stats?.total_keywords ?? 0;
                modal.confirm({
                  title: '全部重新分类',
                  width: 440,
                  content: (
                    <Space direction="vertical" size={8}>
                      <Text>
                        将对所有 <Text strong>{totalCount}</Text> 个关键词进行完全重新分类
                      </Text>
                      <Text type="warning">
                        AI 可能创建新分组或删除空分组
                      </Text>
                      <Text type="danger">
                        此操作不可撤销，建议先备份
                      </Text>
                    </Space>
                  ),
                  okText: '确认重新分类',
                  okType: 'danger',
                  cancelText: '取消',
                  onOk: () => reclassifyAllMut.mutate(),
                });
              }}
            >
              全部重新分类
            </Button>
          </div>
        </div>

        {selectedRowKeys.length > 0 && (
          <div className={styles.batchBar}>
            <span className={styles.selectedCount}>已选 {selectedRowKeys.length} 项</span>
            <Button
              size="small"
              icon={<ThunderboltOutlined />}
              loading={batchAutoClassifyMut.isPending}
              onClick={() => {
                modal.confirm({
                  title: 'AI 自动分类',
                  content: `将对选中的 ${selectedRowKeys.length} 个关键词进行 AI 自动分类，确认继续？`,
                  okText: '开始分类',
                  cancelText: '取消',
                  onOk: () => batchAutoClassifyMut.mutate(selectedRowKeys),
                });
              }}
            >
              批量分类
            </Button>
            <Button size="small" danger onClick={() => {
              modal.confirm({
                title: '批量删除',
                content: `确定要删除选中的 ${selectedRowKeys.length} 个关键词吗？`,
                okText: '删除',
                okType: 'danger',
                cancelText: '取消',
                onOk: () => batchDeleteMut.mutate(selectedRowKeys),
              });
            }}>
              批量删除
            </Button>
            <Button size="small" onClick={() => setSelectedRowKeys([])}>取消选择</Button>
          </div>
        )}

        <div className={styles.tableWrapper}>
          <Table<Keyword>
            rowKey="id"
            columns={columns}
            dataSource={kwData?.items ?? []}
            loading={kwLoading}
            rowSelection={{
              selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys(keys as number[]),
            }}
            pagination={false}
            size="middle"
            scroll={{ y: 'calc(100vh - 440px)' }}
            locale={{ emptyText: <Empty description="暂无关键词，点击「添加」或「批量添加」" /> }}
          />
        </div>
        <div style={{ padding: '8px 16px', borderTop: '1px solid #f0f0f0', textAlign: 'right' }}>
          <Pagination
            current={page}
            pageSize={50}
            total={kwData?.total ?? 0}
            onChange={setPage}
            showTotal={(t) => `共 ${t} 条`}
            size="small"
          />
        </div>
      </div>
    </div>
  );

  // ── Tab 2: Fission ─────────────────────────────────────────────────

  const fissionTab = (
    <div className={styles.fissionContainer}>
      <Card className={styles.fissionInputCard} size="small" title="种子关键词">
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Input
            placeholder="输入种子关键词，AI 将自动裂变生成相关关键词"
            value={fissionSeed}
            onChange={(e) => setFissionSeed(e.target.value)}
            onPressEnter={handleFission}
            size="large"
          />
          <Space wrap>
            <Select
              mode="multiple"
              value={fissionPlatforms}
              onChange={setFissionPlatforms}
              style={{ minWidth: 200, maxWidth: 360 }}
              placeholder="选择目标平台"
              maxTagCount={3}
              options={[
                { value: 'all', label: `全平台 (${platformOptions.length}个)` },
                ...platformOptions,
              ]}
              onSelect={(val) => {
                if (val === 'all') {
                  setFissionPlatforms(platformOptions.map((o) => o.value));
                }
              }}
              onDeselect={(val) => {
                if (val === 'all') {
                  setFissionPlatforms([]);
                }
              }}
            />
            <Select
              value={fissionDepth}
              onChange={setFissionDepth}
              style={{ width: 160 }}
              options={[
                { value: 1, label: '保守裂变 (10-15词)' },
                { value: 2, label: '激进裂变 (20-30词)' },
              ]}
            />
            <Button
              type="primary"
              icon={<ExperimentOutlined />}
              loading={fissionLoading}
              onClick={handleFission}
              disabled={!fissionSeed.trim() || fissionPlatforms.length === 0}
            >
              开始裂变
            </Button>
          </Space>
        </Space>
      </Card>

      {fissionResult && (
        <Card
          className={styles.fissionResultCard}
          size="small"
          title={
            <Space>
              <ExperimentOutlined style={{ color: '#6366f1' }} />
              <span>裂变结果：{fissionResult.seed_keyword}</span>
              <Tag color="purple">{fissionResult.generated.length} 个关键词</Tag>
              <Space size={4}>
                {fissionResult.platforms.map((p) => (
                  <Tag key={p} color="blue" style={{ fontSize: 10 }}>
                    {getPlatformName(p)}
                  </Tag>
                ))}
              </Space>
            </Space>
          }
          extra={
            <Space>
              <Button
                size="small"
                onClick={() =>
                  setSelectedFissionKeys(fissionResult.generated.map((g) => g.keyword))
                }
              >
                全选
              </Button>
              <Button size="small" onClick={() => setSelectedFissionKeys([])}>
                取消
              </Button>
              <Select
                placeholder="选择分组"
                allowClear
                style={{ width: 140 }}
                value={fissionTargetGroup}
                onChange={setFissionTargetGroup}
                options={(groups ?? []).map((g) => ({ value: g.id, label: g.name }))}
              />
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                disabled={selectedFissionKeys.length === 0}
                onClick={handleAcceptFission}
              >
                加入词库 ({selectedFissionKeys.length})
              </Button>
            </Space>
          }
        >
          <div className={styles.fissionCardGrid}>
            {fissionResult.generated.map((g) => {
              const isSelected = selectedFissionKeys.includes(g.keyword);
              return (
                <div
                  key={`${g.platform}-${g.keyword}`}
                  className={`${styles.fissionCard} ${isSelected ? styles.fissionCardSelected : ''}`}
                  onClick={() => {
                    setSelectedFissionKeys((prev) =>
                      isSelected
                        ? prev.filter((k) => k !== g.keyword)
                        : [...prev, g.keyword],
                    );
                  }}
                >
                  <div className={styles.fissionCardHeader}>
                    <Checkbox checked={isSelected} style={{ marginRight: 8, flexShrink: 0 }} />
                    <span className={styles.fissionKeyword}>{g.keyword}</span>
                    <Tag
                      className={styles.fissionPlatform}
                      color="blue"
                      style={{ fontSize: 10, marginRight: 4 }}
                    >
                      {getPlatformName(g.platform)}
                    </Tag>
                    <Tag
                      className={styles.fissionCategory}
                      color={
                        g.category.includes('长尾')
                          ? 'blue'
                          : g.category.includes('相关')
                            ? 'green'
                            : g.category.includes('问句')
                              ? 'orange'
                              : g.category.includes('地域')
                                ? 'magenta'
                                : g.category.includes('热点')
                                  ? 'red'
                                  : 'default'
                      }
                    >
                      {g.category}
                    </Tag>
                  </div>
                  <div className={styles.fissionReason}>{g.reason}</div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {!fissionResult && !fissionLoading && (
        <div className={styles.emptyState}>
          <Empty description="输入种子关键词开始 AI 裂变，生成长尾词、相关词、问句词等" />
        </div>
      )}
    </div>
  );

  // ── Tab 3: Stats ───────────────────────────────────────────────────

  const statsTab = (
    <div className={styles.statsContainer}>
      {stats ? (
        <>
          <div className={styles.statsCards}>
            <div className={styles.statsCard}>
              <div className={styles.statsNumber}>{stats.total_keywords}</div>
              <div className={styles.statsLabel}>总关键词</div>
            </div>
            {stats.by_group.map((g) => (
              <div key={g.group_name} className={styles.statsCard}>
                <div className={styles.statsNumber}>{g.count}</div>
                <div className={styles.statsLabel}>{g.group_name || '未分组'}</div>
              </div>
            ))}
          </div>

          <Card size="small" title="使用状态分布" style={{ marginBottom: 16 }}>
            <Space wrap size="large">
              {stats.by_status.map((s) => {
                const cfg = STATUS_CFG[s.status] || { color: 'default', label: s.status };
                return (
                  <Space key={s.status}>
                    <Tag color={cfg.color}>{cfg.label}</Tag>
                    <Text strong>{s.count}</Text>
                  </Space>
                );
              })}
            </Space>
          </Card>

          <Card
            className={styles.topKeywordsCard}
            size="small"
            title={<><StarOutlined style={{ color: '#faad14' }} /> 高产关键词 Top 10</>}
          >
            {stats.top_performing.length === 0 ? (
              <Empty description="暂无数据，启动爬虫任务后自动统计" />
            ) : (
              stats.top_performing.map((kw, idx) => (
                <div key={kw.keyword} className={styles.topKeywordItem}>
                  <div className={styles.topKwRank} style={{ background: idx < 3 ? '#faad14' : '#6366f1' }}>
                    {idx + 1}
                  </div>
                  <span className={styles.topKwText}>{kw.keyword}</span>
                  <span className={styles.topKwStats}>
                    爬取 {kw.crawled_count} 次 · 产出 {kw.results_count} 条
                  </span>
                </div>
              ))
            )}
          </Card>
        </>
      ) : (
        <div className={styles.emptyState}>
          <Empty description="暂无统计数据" />
        </div>
      )}
    </div>
  );

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div className={styles.container}>
      <PageHeader
        title="关键词管理"
        description="管理关键词库，AI 裂变扩展长尾词/相关词/问句词，直接关联爬虫任务"
        extra={
          <Button
            icon={<RocketOutlined />}
            onClick={() => navigate('/crawler')}
          >
            去爬虫
          </Button>
        }
      />
      <Card style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}
        styles={{ body: { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '0 0 16px 0' } }}>
        <Tabs
          defaultActiveKey="library"
          items={[
            {
              key: 'library',
              label: '关键词库',
              children: libraryTab,
            },
            {
              key: 'fission',
              label: 'AI 裂变',
              children: fissionTab,
            },
            {
              key: 'stats',
              label: '效果统计',
              children: statsTab,
            },
          ]}
          style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}
          tabBarStyle={{ marginBottom: 0, paddingLeft: 16 }}
          tabBarExtraContent={
            <Space style={{ paddingRight: 16 }}>
              <Tag color="blue">{defaultPlatformName}</Tag>
            </Space>
          }
        />
      </Card>

      {/* Group Create/Edit Modal */}
      <Modal
        title={editingGroup ? '编辑分组' : '新建分组'}
        open={groupModalOpen}
        onCancel={() => {
          setGroupModalOpen(false);
          setEditingGroup(null);
          groupForm.resetFields();
        }}
        onOk={() => groupForm.submit()}
        confirmLoading={createGroupMut.isPending || updateGroupMut.isPending}
      >
        <Form
          form={groupForm}
          layout="vertical"
          onFinish={(values) => {
            if (editingGroup) {
              updateGroupMut.mutate({ id: editingGroup.id, data: values });
            } else {
              createGroupMut.mutate(values);
            }
          }}
        >
          <Form.Item name="parent_id" label="父分组（二级分类）">
            <Select
              allowClear
              placeholder="留空则为一级分组"
              options={(groups ?? [])
                .filter((g) => g.parent_id === null && g.id !== editingGroup?.id)
                .map((g) => ({ value: g.id, label: g.name }))}
            />
          </Form.Item>
          <Form.Item name="name" label="分组名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：电商、美妆、旅行" />
          </Form.Item>
          <Form.Item name="color" label="颜色标识" initialValue="#6366f1">
            <ColorPicker showText />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="可选描述" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Keyword Create/Edit Modal */}
      <Modal
        title={editingKeyword ? '编辑关键词' : '添加关键词'}
        open={keywordModalOpen}
        onCancel={() => {
          setKeywordModalOpen(false);
          setEditingKeyword(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={createKwMut.isPending || updateKwMut.isPending}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => {
            if (editingKeyword) {
              updateKwMut.mutate({ id: editingKeyword.id, data: values });
            } else {
              createKwMut.mutate(values);
            }
          }}
        >
          <Form.Item name="keyword" label="关键词" rules={[{ required: true, message: '请输入关键词' }]}>
            <Input placeholder="输入关键词" />
          </Form.Item>
          <Form.Item name="group_id" label="分组">
            <Select
              allowClear
              placeholder="选择分组"
              options={(groups ?? []).map((g) => ({ value: g.id, label: g.name }))}
            />
          </Form.Item>
          <Form.Item name="platform" label="平台" initialValue={defaultPlatform}>
            <Select options={platformOptions} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} placeholder="可选备注" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Batch Keyword Create Modal */}
      <Modal
        title="批量添加关键词"
        open={batchKeywordModalOpen}
        onCancel={() => {
          setBatchKeywordModalOpen(false);
          batchForm.resetFields();
        }}
        onOk={() => batchForm.submit()}
        confirmLoading={batchCreateMut.isPending}
      >
        <Form
          form={batchForm}
          layout="vertical"
          onFinish={(values) => {
            const lines = (values.keywords_text as string)
              .split(/[\n,]/)
              .map((s) => s.trim())
              .filter(Boolean);
            batchCreateMut.mutate({
              keywords: lines,
              group_id: values.group_id,
              platform: values.platform,
            });
          }}
        >
          <Form.Item
            name="keywords_text"
            label="关键词列表"
            rules={[{ required: true, message: '请输入关键词' }]}
            extra="每行一个关键词，或用逗号分隔"
          >
            <Input.TextArea rows={6} placeholder="关键词1&#10;关键词2&#10;关键词3" />
          </Form.Item>
          <Form.Item name="group_id" label="分组">
            <Select
              allowClear
              placeholder="选择分组"
              options={(groups ?? []).map((g) => ({ value: g.id, label: g.name }))}
            />
          </Form.Item>
          <Form.Item name="platform" label="平台" initialValue={defaultPlatform}>
            <Select options={platformOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
