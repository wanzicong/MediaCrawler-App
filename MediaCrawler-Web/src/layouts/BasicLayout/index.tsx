import { useEffect, useMemo, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  DatabaseOutlined,
  DashboardOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MenuOutlined,
  NodeIndexOutlined,
  RocketOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { Breadcrumb, Drawer, Layout, Menu, Typography } from 'antd';
import dayjs from 'dayjs';

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

const breadcrumbMap: Record<string, string> = {
  '/dashboard': '概览',
  '/settings': '配置方案',
  '/crawler': '爬虫任务',
  '/data': '数据中心',
};

const titleMap: Record<string, string> = {
  '/dashboard': `概览 | ${APP_TITLE}`,
  '/settings': `配置方案 | ${APP_TITLE}`,
  '/crawler': `爬虫任务 | ${APP_TITLE}`,
  '/data': `数据中心 | ${APP_TITLE}`,
};

export default function BasicLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const selectedKey = useMemo(() => {
    const match = menuItems.find((item) => location.pathname.startsWith(item.key));
    return match?.key ?? '/dashboard';
  }, [location.pathname]);

  useEffect(() => {
    document.title = titleMap[selectedKey] || APP_TITLE;
  }, [selectedKey]);

  const breadcrumbItems = [
    { title: '控制台' },
    ...(breadcrumbMap[selectedKey] ? [{ title: breadcrumbMap[selectedKey] }] : []),
  ];

  const handleMenuClick = (key: string) => {
    navigate(key);
    setMobileMenuOpen(false);
  };

  const siderMenu = (
    <div className={styles.siderInner}>
      <div className={styles.logo}>
        <NodeIndexOutlined className={styles.logoIcon} />
        {!collapsed && (
          <Typography.Title level={5} className={styles.logoText}>
            MediaCrawler
          </Typography.Title>
        )}
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={({ key }) => handleMenuClick(key)}
        style={{ flex: 1, borderInlineEnd: 'none' }}
      />
      <div className={styles.siderFooter}>
        <span className={styles.version}>v1.0.0</span>
      </div>
    </div>
  );

  return (
    <Layout className={styles.layout} hasSider>
      {/* Desktop Sider */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={220}
        className={`${styles.sider} ${styles.desktopSider}`}
      >
        {siderMenu}
      </Sider>

      {/* Mobile Drawer */}
      <Drawer
        placement="left"
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        width={220}
        styles={{ body: { padding: 0 } }}
        className={styles.mobileDrawer}
      >
        {siderMenu}
      </Drawer>

      <Layout className={styles.mainArea}>
        <Header className={styles.header}>
          <div className={styles.headerLeft}>
            <div
              className={`${styles.trigger} ${styles.mobileMenuBtn}`}
              onClick={() => setMobileMenuOpen(true)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && setMobileMenuOpen(true)}
            >
              <MenuOutlined />
            </div>
            <div
              className={`${styles.trigger} ${styles.desktopTrigger}`}
              onClick={toggleSidebar}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && toggleSidebar()}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </div>
      <Breadcrumb
        items={breadcrumbItems.map((item, idx) => ({
          title: idx === breadcrumbItems.length - 1 ? item.title : <Link to="/dashboard">{item.title}</Link>,
        }))}
      />
          </div>
          <div className={styles.headerRight}>
            <span className={styles.headerTime}>
              {dayjs().format('YYYY-MM-DD HH:mm')}
            </span>
          </div>
        </Header>
        <Content className={styles.content}>
          <div key={location.pathname} className="page-transition">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
