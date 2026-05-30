import { Button, Descriptions, Modal, Space } from 'antd';
import { DeleteOutlined, ExportOutlined } from '@ant-design/icons';
import { getPlatformUrl, PLATFORM_LABELS } from '@/constants';

interface FieldItem {
  key: string;
  label: string;
  value: unknown;
}

interface Props {
  detailRow: Record<string, unknown> | null;
  allFields: FieldItem[];
  renderValue: (key: string, v: unknown) => React.ReactNode;
  onDelete: (recordId: number) => void;
  onClose: () => void;
  platform: string;
}

export default function DataDetailModal({
  detailRow,
  allFields,
  renderValue,
  onDelete,
  onClose,
  platform,
}: Props) {
  const platformUrl = detailRow ? getPlatformUrl(platform, detailRow) : null;
  const platformName = PLATFORM_LABELS[platform] || '平台';

  return (
    <Modal
      title={
        <Space>
          <span>数据详情</span>
          {platformUrl && (
            <Button
              type="primary"
              size="small"
              icon={<ExportOutlined />}
              onClick={() => window.open(platformUrl, '_blank', 'noopener')}
            >
              在{platformName}打开
            </Button>
          )}
        </Space>
      }
      open={!!detailRow}
      onCancel={onClose}
      width={800}
      footer={
        <Space>
          {platformUrl && (
            <Button
              type="primary"
              icon={<ExportOutlined />}
              onClick={() => window.open(platformUrl, '_blank', 'noopener')}
            >
              在{platformName}打开
            </Button>
          )}
          {detailRow && (
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(detailRow.id as number)}
            >
              删除此记录
            </Button>
          )}
          <Button onClick={onClose}>关闭</Button>
        </Space>
      }
    >
      {detailRow && (
        <Descriptions bordered size="small" column={2} style={{ maxHeight: 500, overflow: 'auto' }}>
          {allFields.map((f) => (
            <Descriptions.Item
              key={f.key}
              label={f.label}
              span={f.key === 'desc' || f.key === 'content' || f.key === 'content_text' || f.key === 'image_list' ? 2 : 1}
            >
              {renderValue(f.key, f.value)}
            </Descriptions.Item>
          ))}
        </Descriptions>
      )}
    </Modal>
  );
}
