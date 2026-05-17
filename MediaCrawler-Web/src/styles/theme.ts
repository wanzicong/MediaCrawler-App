import type { ThemeConfig } from 'antd';

const BRAND = {
  primary: '#5B5FE3',
  primaryHover: '#4A4ECF',
  primaryActive: '#3C3FB8',
  accent: '#F59E0B',
  success: '#10B981',
  error: '#EF4444',
  warning: '#F59E0B',
  info: '#6366F1',
};

const SIDEBAR = {
  bg: '#0F172A',
  activeBg: 'rgba(91, 95, 227, 0.15)',
  activeBorder: '#5B5FE3',
  text: '#E2E8F0',
  subText: '#94A3B8',
};

export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: BRAND.primary,
    colorSuccess: BRAND.success,
    colorError: BRAND.error,
    colorWarning: BRAND.warning,
    colorInfo: BRAND.info,
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,
    fontFamily: `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif`,
    fontSize: 14,
    colorBgContainer: '#FFFFFF',
    colorBgLayout: '#F1F5F9',
    colorBgElevated: '#FFFFFF',
    colorBorderSecondary: '#E2E8F0',
    lineHeight: 1.6,
    controlHeight: 36,
    boxShadow: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
    boxShadowSecondary: '0 4px 12px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04)',
  },
  components: {
    Layout: {
      siderBg: SIDEBAR.bg,
      triggerBg: '#1E293B',
      triggerColor: SIDEBAR.text,
      headerBg: '#FFFFFF',
      headerHeight: 56,
      headerPadding: '0 24px',
      bodyBg: '#F1F5F9',
    },
    Menu: {
      darkItemBg: SIDEBAR.bg,
      darkItemColor: SIDEBAR.text,
      darkItemSelectedBg: SIDEBAR.activeBg,
      darkItemSelectedColor: BRAND.primary,
      darkItemHoverBg: 'rgba(255,255,255,0.04)',
      itemBorderRadius: 8,
      itemMarginInline: 8,
      iconSize: 18,
    },
    Card: {
      paddingLG: 24,
      borderRadiusLG: 12,
    },
    Table: {
      headerBg: '#F8FAFC',
      headerColor: '#475569',
      borderColor: '#E2E8F0',
      rowHoverBg: 'rgba(91, 95, 227, 0.03)',
      cellPaddingBlock: 12,
      cellPaddingInline: 16,
    },
    Button: {
      primaryShadow: '0 2px 4px rgba(91, 95, 227, 0.3)',
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
      linkColor: '#64748B',
      separatorColor: '#94A3B8',
    },
  },
};

export { BRAND, SIDEBAR };
