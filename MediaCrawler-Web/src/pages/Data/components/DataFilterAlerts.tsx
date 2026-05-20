import { Alert, Tag } from 'antd';
import { FIELD_LABELS, PLATFORM_LABELS } from '@/constants';

interface Props {
  filterTaskId: string | null;
  filterContentId: string | null;
  kind: string;
  platform: string;
  contentIdField: string;
  onClear: () => void;
}

export default function DataFilterAlerts({
  filterTaskId,
  filterContentId,
  kind,
  platform,
  contentIdField,
  onClear,
}: Props) {
  return (
    <>
      {filterTaskId && (
        <Alert
          type="info"
          showIcon
          closable
          onClose={onClear}
          message={
            <span>
              正在查看任务 <Tag>#{filterTaskId}</Tag> 的{' '}
              {PLATFORM_LABELS[platform] || platform} 内容数据
            </span>
          }
          style={{ marginBottom: 16 }}
        />
      )}
      {filterContentId && kind === 'comments' && (
        <Alert
          type="info"
          showIcon
          closable
          onClose={onClear}
          message={
            <span>
              正在查看 {FIELD_LABELS[contentIdField] || contentIdField} 为{' '}
              <Tag>{filterContentId}</Tag> 的评论
            </span>
          }
          style={{ marginBottom: 16 }}
        />
      )}
      {filterContentId && kind === 'contents' && (
        <Alert
          type="info"
          showIcon
          closable
          onClose={onClear}
          message={
            <span>
              正在查看 {FIELD_LABELS[contentIdField] || contentIdField} 为{' '}
              <Tag>{filterContentId}</Tag> 的内容
            </span>
          }
          style={{ marginBottom: 16 }}
        />
      )}
    </>
  );
}
