import type { ThemeConfig } from 'antd';

const BRAND = {
  primary: '#6366F1',
  primaryHover: '#5558E6',
  primaryActive: '#4A4ED6',
  accent: '#F59E0B',
  success: '#10B981',
  error: '#EF4444',
  warning: '#F59E0B',
  info: '#6366F1',
};

const SIDEBAR = {
  bg: '#FAFBFC',
  activeBg: 'rgba(99, 102, 241, 0.08)',
  activeBorder: '#6366F1',
  text: '#1E293B',
  subText: '#64748B',
};

export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: BRAND.primary,
    colorSuccess: BRAND.success,
    colorError: BRAND.error,
    colorWarning: BRAND.warning,
    colorInfo: BRAND.info,
    borderRadius: 8,
    borderRadiusLG: 8,
    borderRadiusSM: 6,
    fontFamily: `"Inter", system-ui, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif`,
    fontSize: 14,
    colorBgContainer: '#FFFFFF',
    colorBgLayout: '#F5F6FA',
    colorBgElevated: '#FFFFFF',
    colorTextBase: '#1E293B',
    colorTextSecondary: '#64748B',
    colorBorder: '#E2E8F0',
    colorBorderSecondary: '#E2E8F0',
    lineHeight: 1.6,
    controlHeight: 36,
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.03)',
    boxShadowSecondary: '0 4px 12px rgba(0, 0, 0, 0.04), 0 2px 4px rgba(0, 0, 0, 0.03)',
  },
  components: {
    Layout: {
      siderBg: 'transparent',
      triggerBg: '#FFFFFF',
      triggerColor: SIDEBAR.text,
      headerBg: '#FFFFFF',
      headerHeight: 56,
      headerPadding: '0 24px',
      bodyBg: '#F5F6FA',
    },
    Menu: {
      itemBg: 'transparent',
      itemColor: SIDEBAR.subText,
      itemHoverColor: SIDEBAR.text,
      itemHoverBg: 'rgba(99, 102, 241, 0.04)',
      itemSelectedBg: 'transparent',
      itemSelectedColor: 'transparent',
      itemActiveBg: 'transparent',
      itemBorderRadius: 10,
      itemMarginInline: 10,
      itemHeight: 44,
      iconSize: 20,
      subMenuItemBg: 'transparent',
    },
    Card: {
      paddingLG: 24,
      borderRadiusLG: 8,
    },
    Table: {
      headerBg: '#F8FAFC',
      headerColor: '#475569',
      borderColor: '#E2E8F0',
      rowHoverBg: 'rgba(99, 102, 241, 0.02)',
      cellPaddingBlock: 12,
      cellPaddingInline: 16,
    },
    Button: {
      primaryShadow: '0 2px 0 rgba(99, 102, 241, 0.1)',
      fontWeight: 500,
      borderRadius: 8,
      controlHeight: 36,
    },
    Tag: {
      borderRadiusSM: 4,
    },
    Statistic: {
      titleFontSize: 12,
      contentFontSize: 20,
    },
    Tabs: {
      horizontalMargin: '0',
      cardPadding: '8px 16px',
    },
    Breadcrumb: {
      lastItemColor: BRAND.primary,
      linkColor: SIDEBAR.subText,
      separatorColor: '#CBD5E1',
    },
  },
};

export { BRAND, SIDEBAR };
