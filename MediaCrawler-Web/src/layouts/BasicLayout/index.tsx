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
  RobotOutlined,
  SettingOutlined,
  TagsOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { Breadcrumb, Drawer, Layout, Menu, Typography } from 'antd';
import type { MenuProps } from 'antd';
import dayjs from 'dayjs';

import { APP_TITLE } from '@/constants';
import { useAppStore } from '@/stores/useAppStore';

import styles from './index.module.less';

const { Header, Sider, Content } = Layout;

const menuGradients: Record<string, { from: string; to: string; bg: string }> = {
  '/dashboard': { from: '#FF6B6B', to: '#FF8E53', bg: 'linear-gradient(135deg, #FFF1F0, #FFF7F5)' },
  '/settings':  { from: '#10B981', to: '#059669', bg: 'linear-gradient(135deg, #ECFDF5, #F0FDF6)' },
  '/keywords':  { from: '#8B5CF6', to: '#7C3AED', bg: 'linear-gradient(135deg, #F5F3FF, #FAF8FF)' },
  '/crawler':   { from: '#3B82F6', to: '#2563EB', bg: 'linear-gradient(135deg, #EFF6FF, #F5F9FF)' },
  '/data':      { from: '#06B6D4', to: '#0891B2', bg: 'linear-gradient(135deg, #ECFEFF, #F0FDFF)' },
  '/ai-chat':   { from: '#EC4899', to: '#DB2777', bg: 'linear-gradient(135deg, #FDF2F8, #FFF5FA)' },
};

const menuItemDefs = [
  { key: '/dashboard', icon: <DashboardOutlined />,  label: '概览' },
  { key: '/settings',  icon: <SettingOutlined />,    label: '配置方案' },
  { key: '/keywords',  icon: <TagsOutlined />,         label: '关键词管理' },
  { key: '/crawler',   icon: <RocketOutlined />,       label: '爬虫任务' },
  { key: '/data',      icon: <DatabaseOutlined />,     label: '数据中心' },
  { key: '/ai-chat',   icon: <RobotOutlined />,        label: 'AI 对话' },
];

const breadcrumbMap: Record<string, string> = {
  '/dashboard': '概览',
  '/settings': '配置方案',
  '/keywords': '关键词管理',
  '/crawler': '爬虫任务',
  '/data': '数据中心',
  '/ai-chat': 'AI 对话',
};

const titleMap: Record<string, string> = {
  '/dashboard': `概览 | ${APP_TITLE}`,
  '/settings': `配置方案 | ${APP_TITLE}`,
  '/keywords': `关键词管理 | ${APP_TITLE}`,
  '/crawler': `爬虫任务 | ${APP_TITLE}`,
  '/data': `数据中心 | ${APP_TITLE}`,
  '/ai-chat': `AI 对话 | ${APP_TITLE}`,
};

export default function BasicLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const selectedKey = useMemo(() => {
    const match = menuItemDefs.find((item) => location.pathname.startsWith(item.key));
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

  const menuItems: MenuProps['items'] = menuItemDefs.map(({ key, icon, label }) => {
    const g = menuGradients[key];
    const isActive = selectedKey === key;
    return {
      key,
      icon: (
        <span
          className={styles.menuIcon}
          style={{
            background: `linear-gradient(135deg, ${g.from}, ${g.to})`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: isActive ? `drop-shadow(0 0 8px ${g.from}40)` : undefined,
          }}
        >
          {icon}
        </span>
      ),
      label: isActive ? (
        <span className={styles.menuLabel} style={{ fontWeight: 600, color: '#1E293B' }}>
          {label}
        </span>
      ) : (
        <span className={styles.menuLabel}>{label}</span>
      ),
      className: `${styles.menuItem} ${isActive ? styles.menuItemActive : ''}`,
    };
  });

  const siderMenu = (
    <div className={styles.siderInner}>
      {/* Logo */}
      <div className={styles.logo}>
        <div className={styles.logoIconBox}>
          <NodeIndexOutlined className={styles.logoIcon} />
        </div>
        {!collapsed && (
          <div className={styles.logoTextGroup}>
            <Typography.Title level={5} className={styles.logoText}>
              MediaCrawler
            </Typography.Title>
            <span className={styles.logoSub}>控制台</span>
          </div>
        )}
      </div>

      {/* Menu */}
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={({ key }) => handleMenuClick(key)}
        className={styles.menu}
      />

      {/* Footer */}
      <div className={styles.siderFooter}>
        <span className={styles.version}>v1.0.0</span>
      </div>
    </div>
  );

  return (
    <Layout className={styles.layout} hasSider>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={240}
        className={`${styles.sider} ${styles.desktopSider}`}
      >
        {siderMenu}
      </Sider>

      <Drawer
        placement="left"
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        width={240}
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
