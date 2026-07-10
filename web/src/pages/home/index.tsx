import { useAccessLevel } from '@/hooks/use-access-level';
import { PageContainer } from '@/layouts/components/page-container';
import { Routes } from '@/routes';
import { useEffect } from 'react';
import { useNavigate } from 'react-router';
import { Applications } from './applications';
import { NextBanner } from './banner';
import { Datasets } from './datasets';

const Home = () => {
  const { isKbOnly, isLoading, isError, error } = useAccessLevel();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !isError && isKbOnly) {
      navigate(Routes.Datasets, { replace: true });
    }
  }, [isLoading, isError, isKbOnly, navigate]);

  if (isError) {
    return (
      <PageContainer>
        <div className="flex flex-col items-center justify-center gap-3 py-20 text-center">
          <p className="text-base font-medium">加载用户信息失败</p>
          <p className="max-w-lg text-sm text-state-error break-words">
            {error?.message || '未知错误'}
          </p>
        </div>
      </PageContainer>
    );
  }

  // kb_only 跳转中：不渲染会拉 /chats 的首页模块
  if (isLoading || isKbOnly) {
    return null;
  }

  return (
    <PageContainer>
      <article>
        <header className="mb-8">
          <NextBanner />
        </header>

        <Datasets />
        <Applications />
      </article>
    </PageContainer>
  );
};

export default Home;
