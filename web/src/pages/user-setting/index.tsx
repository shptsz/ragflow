import { SideBar } from './sidebar';

import { useAccessLevel } from '@/hooks/use-access-level';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';
import { useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router';

const profilePath = `${Routes.UserSetting}/profile`;
const teamPath = `${Routes.UserSetting}${Routes.Team}`;

const UserSetting = () => {
  const { isKbOnly, isLoading, isError, error } = useAccessLevel();
  const { pathname } = useLocation();
  const navigate = useNavigate();

  const allowed =
    pathname === profilePath ||
    pathname.startsWith(`${profilePath}/`) ||
    pathname === teamPath ||
    pathname.startsWith(`${teamPath}/`);
  const shouldRedirect = !isLoading && !isError && isKbOnly && !allowed;

  useEffect(() => {
    if (shouldRedirect) {
      navigate(profilePath, { replace: true });
    }
  }, [shouldRedirect, navigate]);

  if (isError) {
    return (
      <div className="flex size-full flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="text-sm text-state-error">
          {error?.message || '加载用户信息失败'}
        </p>
      </div>
    );
  }

  if (isLoading || shouldRedirect) {
    return null;
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
