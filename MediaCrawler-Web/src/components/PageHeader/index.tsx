import type { ReactNode } from 'react';
import { Typography } from 'antd';

import styles from './index.module.less';

interface PageHeaderProps {
  title: string;
  description?: string;
  extra?: ReactNode;
}

export default function PageHeader({ title, description, extra }: PageHeaderProps) {
  return (
    <div className={styles.container}>
      <div className={styles.left}>
        <Typography.Title level={4} className={styles.title}>
          {title}
        </Typography.Title>
        {description && (
          <Typography.Text type="secondary">{description}</Typography.Text>
        )}
      </div>
      {extra && <div className={styles.extra}>{extra}</div>}
    </div>
  );
}
