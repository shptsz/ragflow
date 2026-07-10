import { useAccessLevel } from '@/hooks/use-access-level';
import { Routes } from '@/routes';
import type { ComponentType } from 'react';
import { Navigate, Outlet } from 'react-router';

/** kb_only 用户访问受限路由时重定向到知识库 */
export function RequireFullAccess({
  children,
  redirectTo = Routes.Datasets,
}: {
  children?: React.ReactNode;
  redirectTo?: string;
}) {
  const { isKbOnly } = useAccessLevel();
  if (isKbOnly) {
    return <Navigate to={redirectTo} replace />;
  }
  return children ? <>{children}</> : <Outlet />;
}

/** 包装 lazy 路由 importer，在页面外再套一层 kb_only 访问守卫 */
export function withRequireFullAccess(
  importer: () => Promise<{ default: ComponentType<any> }>,
) {
  return async () => {
    const mod = await importer();
    const Page = mod.default;
    function Guarded(props: any) {
      return (
        <RequireFullAccess>
          <Page {...props} />
        </RequireFullAccess>
      );
    }
    Guarded.displayName = `RequireFullAccess(${Page.displayName || Page.name || 'Page'})`;
    return { default: Guarded };
  };
}
