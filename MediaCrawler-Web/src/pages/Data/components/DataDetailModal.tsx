import { Button, Descriptions, Modal, Space } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';

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
}

export default function DataDetailModal({
  detailRow,
  allFields,
  renderValue,
  onDelete,
  onClose,
}: Props) {
  return (
    <Modal
      title="数据详情"
      open={!!detailRow}
      onCancel={onClose}
      width={800}
      footer={
        <Space>
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
