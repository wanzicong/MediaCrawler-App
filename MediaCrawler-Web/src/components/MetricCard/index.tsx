import { Card, Skeleton } from 'antd';
import type { ReactNode } from 'react';
import { colorToRgba } from '@/utils/format';

import styles from './index.module.less';

interface MetricCardProps {
  title: string;
  value: ReactNode;
  icon: ReactNode;
  color: string;
  loading?: boolean;
  extra?: ReactNode;
  subtitle?: string;
  onClick?: () => void;
}

export default function MetricCard({
  title,
  value,
  icon,
  color,
  loading,
  extra,
  subtitle,
  onClick,
}: MetricCardProps) {
  return (
    <Card
      className={onClick ? `${styles.card} ${styles.clickable}` : styles.card}
      style={{ borderLeft: `3px solid ${color}` }}
      onClick={onClick}
      hoverable
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 1 }} title={{ width: '60%' }} />
      ) : (
        <>
          <div className={styles.header}>
            <span className={styles.title}>{title}</span>
            <span className={styles.iconCircle} style={{ background: colorToRgba(color, 0.08), color }}>
              {icon}
            </span>
          </div>
          <div className={styles.value}>{value}</div>
          {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
          {extra && <div className={styles.extra}>{extra}</div>}
        </>
      )}
    </Card>
  );
}
