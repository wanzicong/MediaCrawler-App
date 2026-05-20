import { useEffect, useRef } from 'react';
import { Button, Input, Select, Space, Tag } from 'antd';

interface KindOption {
  value: string;
  label: string;
}

interface PlatformOption {
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
  onPlatformChange: (v: string) => void;
  onKindChange: (v: string) => void;
  onKeywordChange: (v: string) => void;
  onSearch: (v: string) => void;
  onClearFilters: () => void;
}

export default function DataFilterBar({
  platform,
  platforms,
  kind,
  kinds,
  keyword,
  dataTotal,
  hasFilters,
  onPlatformChange,
  onKindChange,
  onKeywordChange,
  onSearch,
  onClearFilters,
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
      <Input.Search
        placeholder="标题关键词（实时搜索）"
        allowClear
        style={{ width: 220 }}
        value={keyword}
        onChange={(e) => onKeywordChange(e.target.value)}
        onSearch={onSearch}
      />
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
