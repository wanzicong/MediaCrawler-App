import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Skeleton } from 'antd';

import BasicLayout from '@/layouts/BasicLayout';

const DashboardPage = lazy(() => import('@/pages/Dashboard'));
const SettingsPage = lazy(() => import('@/pages/Settings'));
const CrawlerPage = lazy(() => import('@/pages/Crawler'));
const DataPage = lazy(() => import('@/pages/Data'));
const NotFoundPage = lazy(() => import('@/pages/NotFound'));

function PageLoader() {
  return (
    <div style={{ padding: 48 }}>
      <Skeleton active paragraph={{ rows: 10 }} />
    </div>
  );
}

function withSuspense(node: ReactNode) {
  return <Suspense fallback={<PageLoader />}>{node}</Suspense>;
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <BasicLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      {
        path: 'dashboard',
        element: withSuspense(<DashboardPage />),
      },
      {
        path: 'settings',
        element: withSuspense(<SettingsPage />),
      },
      {
        path: 'crawler',
        element: withSuspense(<CrawlerPage />),
      },
      {
        path: 'data',
        element: withSuspense(<DataPage />),
      },
    ],
  },
  {
    path: '*',
    element: withSuspense(<NotFoundPage />),
  },
]);
