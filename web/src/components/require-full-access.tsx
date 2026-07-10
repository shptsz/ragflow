import { useAccessLevel } from '@/hooks/use-access-level';
import { Routes } from '@/routes';
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
