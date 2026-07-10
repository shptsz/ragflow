import { Navigate, Outlet, useLocation } from 'react-router';
import { SideBar } from './sidebar';

import { useAccessLevel } from '@/hooks/use-access-level';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';

const profilePath = `${Routes.UserSetting}/profile`;

const UserSetting = () => {
  const { isKbOnly } = useAccessLevel();
  const { pathname } = useLocation();

  // kb_only 仅允许个人资料页，其余设置子路由重定向
  if (
    isKbOnly &&
    pathname !== profilePath &&
    !pathname.startsWith(`${profilePath}/`)
  ) {
    return <Navigate to={profilePath} replace />;
  }

  return (
    <section className="pt-8 size-full grid grid-cols-[4rem_minmax(0,1fr)] md:grid-cols-[303px_minmax(0,1fr)] grid-rows-1 min-w-0">
      <SideBar />

      <div
        className={cn(
          'pr-2 md:pr-6 pb-6 flex flex-1 min-w-0 rounded-lg overflow-hidden',
        )}
      >
        <Outlet />
      </div>
    </section>
  );
};

export default UserSetting;
