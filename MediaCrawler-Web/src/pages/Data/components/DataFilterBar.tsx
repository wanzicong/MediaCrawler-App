import { useEffect, useRef } from 'react';
import { Button, Input, Select, Space, Tag } from 'antd';
import { SortAscendingOutlined } from '@ant-design/icons';
import type { TaskInfo } from '@/api/modules/dataDb';

interface KindOption {
  value: string;
  label: string;
}

interface PlatformOption {
  value: string;
  label: string;
}

export interface SortOption {
  value: string;
  label: string;
}

interface Props {
  platform: string;
  platforms: PlatformOption[];
  kind: string;
  kinds: KindOption[];
  keyword: string;
  dataTotal?: number;
  hasFilters: boolean;
  sortOptions: SortOption[];
  orderBy?: string;
  orderDirection?: string;
  filterTaskId: string | null;
  availableTasks: TaskInfo[];
  tasksLoading: boolean;
  onPlatformChange: (v: string) => void;
  onKindChange: (v: string) => void;
  onKeywordChange: (v: string) => void;
  onSearch: (v: string) => void;
  onClearFilters: () => void;
  onOrderByChange?: (v: string) => void;
  onOrderDirectionChange?: (v: string) => void;
  onTaskIdChange: (v: string | null) => void;
}

export default function DataFilterBar({
  platform,
  platforms,
  kind,
  kinds,
  keyword,
  dataTotal,
  hasFilters,
  sortOptions,
  orderBy,
  orderDirection,
  filterTaskId,
  availableTasks,
  tasksLoading,
  onPlatformChange,
  onKindChange,
  onKeywordChange,
  onSearch,
  onClearFilters,
  onOrderByChange,
  onOrderDirectionChange,
  onTaskIdChange,
}: Props) {
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

 useEffect(() => {
   if (timerRef.current) clearTimeout(timerRef.current);
   timerRef.current = setTimeout(() => {
     onSearch(keyword);
   }, 300);
   return () => {
     if (timerRef.current) clearTimeout(timerRef.current);
   };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyword]);

  return (
    <Space wrap style={{ marginBottom: 16 }}>
      <Select
        style={{ width: 140 }}
        value={platform}
        options={platforms.map((p) => ({ value: p.value, label: p.label }))}
        onChange={(v) => {
          onPlatformChange(v);
          onKindChange('contents');
        }}
      />
      <Select
        style={{ width: 120 }}
        value={kind}
        options={kinds.map((k) => ({ value: k.value, label: k.label }))}
        onChange={onKindChange}
      />
      <Select
        style={{ minWidth: 200, maxWidth: 320 }}
        placeholder="筛选任务（按关键词）"
        allowClear
        showSearch
        loading={tasksLoading}
        value={filterTaskId || undefined}
        onChange={(v) => onTaskIdChange(v ?? null)}
        filterOption={(input, option) => {
          const label = String(option?.label ?? '').toLowerCase();
          return label.includes(input.toLowerCase());
        }}
        options={availableTasks.map((t) => ({
          value: String(t.task_id),
          label: `#${t.task_id} ${t.keywords ? `— ${t.keywords.slice(0, 40)}${t.keywords.length > 40 ? '...' : ''}` : ''} (${t.record_count}条)`,
        }))}
        notFoundContent={tasksLoading ? '加载中...' : '当前数据无关联任务'}
      />
      <Input.Search
        placeholder="标题关键词（实时搜索）"
        allowClear
        style={{ width: 220 }}
        value={keyword}
        onChange={(e) => onKeywordChange(e.target.value)}
        onSearch={onSearch}
      />
      {sortOptions.length > 0 && kind === 'contents' && (
        <>
          <Select
            style={{ width: 120 }}
            placeholder="排序字段"
            allowClear
            value={orderBy}
            options={sortOptions}
            onChange={(v) => onOrderByChange?.(v ?? '')}
          />
          {orderBy && (
            <Select
              style={{ width: 90 }}
              value={orderDirection ?? 'desc'}
              options={[
                { value: 'desc', label: '降序' },
                { value: 'asc', label: '升序' },
              ]}
              onChange={(v) => onOrderDirectionChange?.(v)}
            />
          )}
        </>
      )}
      {dataTotal != null && (
        <Tag color="blue">共 {dataTotal} 条</Tag>
      )}
      {hasFilters && (
        <Button size="small" onClick={onClearFilters}>
          清除筛选
        </Button>
      )}
    </Space>
  );
}
