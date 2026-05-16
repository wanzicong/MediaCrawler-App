import type { ReactNode } from 'react';
import { Typography } from 'antd';

interface PageHeaderProps {
  title: string;
  description?: string;
  extra?: ReactNode;
}

export default function PageHeader({ title, description, extra }: PageHeaderProps) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
      <div>
        <Typography.Title level={4} style={{ marginBottom: 4 }}>
          {title}
        </Typography.Title>
        {description && (
          <Typography.Text type="secondary">{description}</Typography.Text>
        )}
      </div>
      {extra}
    </div>
  );
}
