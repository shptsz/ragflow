import { Outlet, Navigate, useLocation } from 'react-router';
import { useAccessLevel } from '@/hooks/use-access-level';
import { Routes } from '@/routes';
import { Header } from './components/header';

export function RootLayoutContainer({ children }: React.PropsWithChildren) {
  return (
    <div className="size-full min-w-0 grid grid-flow-col grid-cols-1 grid-rows-[auto_1fr]">
      <Header className="px-5 py-4" />

      <main className="size-full min-w-0 overflow-hidden">{children}</main>
    </div>
  );
}

/** kb_only 允许的路径：知识库与用户设置（设置内再细粒度限制） */
function isKbOnlyAllowedPath(pathname: string): boolean {
  if (
    pathname.startsWith(Routes.Datasets) ||
    pathname.startsWith(Routes.DatasetBase)
  ) {
    return true;
  }
  // 数据源详情是 UserSetting 的兄弟路由，不走设置布局守卫
  if (pathname.includes(Routes.DataSourceDetailPage)) {
    return false;
  }
  return pathname.startsWith(Routes.UserSetting);
}

export default function RootLayout() {
  const { isKbOnly } = useAccessLevel();
  const { pathname } = useLocation();

  if (isKbOnly && !isKbOnlyAllowedPath(pathname)) {
    return (
      <RootLayoutContainer>
        <Navigate to={Routes.Datasets} replace />
      </RootLayoutContainer>
    );
  }

  return (
    <RootLayoutContainer>
      <Outlet />
    </RootLayoutContainer>
  );
}
