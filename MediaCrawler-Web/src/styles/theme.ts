import type { ThemeConfig } from 'antd';

const BRAND = {
  primary: '#D97757',
  primaryHover: '#C06845',
  primaryActive: '#A8583A',
  accent: '#F59E0B',
  success: '#10B981',
  error: '#EF4444',
  warning: '#F59E0B',
  info: '#D97757',
};

const SIDEBAR = {
  bg: '#1A1A1A',
  activeBg: 'rgba(217, 119, 87, 0.15)',
  activeBorder: '#D97757',
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
    borderRadiusLG: 8,
    borderRadiusSM: 6,
    fontFamily: `"Inter", "Anthropic Sans", system-ui, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif`,
    fontSize: 14,
    colorBgContainer: '#FFFFFF',
    colorBgLayout: '#F8F8F6',
    colorBgElevated: '#FFFFFF',
    colorTextBase: '#121212',
    colorTextSecondary: '#8C8C82',
    colorBorder: '#E8E8E2',
    colorBorderSecondary: '#E8E8E2',
    lineHeight: 1.6,
    controlHeight: 36,
    boxShadow: '0 1px 3px rgba(26, 24, 20, 0.06), 0 1px 2px rgba(26, 24, 20, 0.04)',
    boxShadowSecondary: '0 4px 12px rgba(26, 24, 20, 0.06), 0 2px 4px rgba(26, 24, 20, 0.04)',
  },
  components: {
    Layout: {
      siderBg: SIDEBAR.bg,
      triggerBg: '#2A2A2A',
      triggerColor: SIDEBAR.text,
      headerBg: '#FFFFFF',
      headerHeight: 56,
      headerPadding: '0 24px',
      bodyBg: '#F8F8F6',
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
      borderRadiusLG: 8,
    },
    Table: {
      headerBg: '#FAFAF8',
      headerColor: '#475569',
      borderColor: '#E8E8E2',
      rowHoverBg: 'rgba(217, 119, 87, 0.03)',
      cellPaddingBlock: 12,
      cellPaddingInline: 16,
    },
    Button: {
      primaryShadow: '0 2px 0 rgba(217, 119, 87, 0.1)',
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
      lastItemColor: '#D97757',
      linkColor: '#8C8C82',
      separatorColor: '#B0B0A8',
    },
  },
};

export { BRAND, SIDEBAR };
