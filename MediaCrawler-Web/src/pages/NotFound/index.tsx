import { Button, Result, theme } from 'antd';
import { useNavigate } from 'react-router-dom';

export default function NotFoundPage() {
  const navigate = useNavigate();
  const { token } = theme.useToken();

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: token.colorBgLayout,
      }}
    >
      <Result
        status="404"
        title="404"
        subTitle="抱歉，您访问的页面不存在或已被移除"
        extra={
          <Button type="primary" size="large" onClick={() => navigate('/dashboard')}>
            返回概览
          </Button>
        }
      />
    </div>
  );
}
