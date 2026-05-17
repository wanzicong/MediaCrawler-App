import { Card, Typography, theme } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  PlayCircleOutlined,
  ApiOutlined,
  DatabaseOutlined,
  RightOutlined,
} from '@ant-design/icons';

export default function DashboardQuickActions() {
  const navigate = useNavigate();
  const { token } = theme.useToken();

  const actions = [
    { label: '启动爬虫', description: '配置并启动新的爬取任务', icon: <PlayCircleOutlined />, path: '/crawler' },
    { label: '配置方案', description: '管理平台登录与爬取偏好', icon: <ApiOutlined />, path: '/settings' },
    { label: '数据中心', description: '查询已爬取的结构化数据', icon: <DatabaseOutlined />, path: '/data' },
  ];

  return (
    <Card title='快捷操作' size="small">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {actions.map((action, idx) => (
          <div
            key={action.path}
            onClick={() => navigate(action.path)}
            style={{
              display: 'flex',
              alignItems: "center",
              gap: 12,
              padding: '12px 0',
              cursor: 'pointer',
              borderBottom: idx < actions.length - 1 ? `1px solid ${token.colorBorderSecondary}` : 'none',
              transition: 'background 0.15s',
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = token.colorFillAlter; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = ""; }}
          >
            <span style={{ color: token.colorPrimary, fontSize: 18, flexShrink: 0 }}>
              {action.icon}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <Typography.Text strong style={{ display: 'block' }}>{action.label}</Typography.Text>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {action.description}
              </Typography.Text>
            </div>
            <RightOutlined style={{ color: token.colorBorderSecondary, fontSize: 12 }} />
          </div>
        ))}
      </div>
    </Card>
  );
}