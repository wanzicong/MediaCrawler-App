import type { ThemeConfig } from 'antd';

/** Ant Design 主题令牌（与控制台深色侧栏搭配） */
export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1677ff',
    borderRadius: 6,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif",
  },
  components: {
    Layout: {
      siderBg: '#001529',
      triggerBg: '#002140',
    },
  },
};
