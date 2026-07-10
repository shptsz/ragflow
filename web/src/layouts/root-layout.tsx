import { useAccessLevel } from '@/hooks/use-access-level';
import { Routes } from '@/routes';
import { useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router';
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
  if (pathname.includes(Routes.DataSourceDetailPage)) {
    return false;
  }
  return pathname.startsWith(Routes.UserSetting);
}

function AccessLoadingFallback() {
  return (
    <div className="flex size-full items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-border-button border-t-transparent" />
    </div>
  );
}

function AccessErrorFallback({ message }: { message: string }) {
  return (
    <div className="flex size-full flex-col items-center justify-center gap-3 px-6 text-center">
      <p className="text-base font-medium text-text-primary">
        加载用户信息失败
      </p>
      <p className="max-w-lg text-sm text-state-error break-words">{message}</p>
      <button
        type="button"
        className="rounded-md border border-border-button px-3 py-1.5 text-sm hover:bg-bg-card"
        onClick={() => window.location.reload()}
      >
        刷新重试
      </button>
    </div>
  );
}

export default function RootLayout() {
  const { isKbOnly, isLoading, isError, error } = useAccessLevel();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const shouldRedirect =
    !isLoading && !isError && isKbOnly && !isKbOnlyAllowedPath(pathname);

  useEffect(() => {
    if (shouldRedirect) {
      navigate(Routes.Datasets, { replace: true });
    }
  }, [shouldRedirect, navigate]);

  if (isError) {
    return (
      <RootLayoutContainer>
        <AccessErrorFallback
          message={error?.message || '未知错误，请检查后端服务或重新登录'}
        />
      </RootLayoutContainer>
    );
  }

  if (isLoading || shouldRedirect) {
    return (
      <RootLayoutContainer>
        <AccessLoadingFallback />
      </RootLayoutContainer>
    );
  }

  return (
    <RootLayoutContainer>
      <Outlet />
    </RootLayoutContainer>
  );
}
