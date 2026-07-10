import { PageContainer } from '@/layouts/components/page-container';
import { useAccessLevel } from '@/hooks/use-access-level';
import { Routes } from '@/routes';
import { Navigate } from 'react-router';
import { Applications } from './applications';
import { NextBanner } from './banner';
import { Datasets } from './datasets';

const Home = () => {
  const { isKbOnly } = useAccessLevel();

  if (isKbOnly) {
    return <Navigate to={Routes.Datasets} replace />;
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
