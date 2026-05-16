import { useMemo } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  DatabaseOutlined,
  DashboardOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RocketOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Layout, Menu, theme, Typography } from 'antd';

import { APP_TITLE } from '@/constants';
import { useAppStore } from '@/stores/useAppStore';

import styles from './index.module.less';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '概览' },
  { key: '/settings', icon: <SettingOutlined />, label: '配置方案' },
  { key: '/crawler', icon: <RocketOutlined />, label: '爬虫任务' },
  { key: '/data', icon: <DatabaseOutlined />, label: '数据中心' },
];

export default function BasicLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const selectedKey = useMemo(() => {
    const match = menuItems.find((item) => location.pathname.startsWith(item.key));
    return match?.key ?? '/dashboard';
  }, [location.pathname]);

  return (
    <Layout className={styles.layout}>
      <Sider trigger={null} collapsible collapsed={collapsed} width={220}>
        <div className={styles.logo}>
          <Typography.Title level={5} className={styles.logoText}>
            {collapsed ? 'MC' : APP_TITLE}
          </Typography.Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className={styles.header} style={{ background: colorBgContainer }}>
          <div
            className={styles.trigger}
            onClick={toggleSidebar}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && toggleSidebar()}
          >
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </div>
          <Typography.Text type="secondary">自媒体数据采集控制台</Typography.Text>
        </Header>
        <Content
          className={styles.content}
          style={{
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
