import { CardContainer } from '@/components/card-container';
import { EmptyCardType } from '@/components/empty/constant';
import { EmptyAppCard } from '@/components/empty/empty';
import ListFilterBar from '@/components/list-filter-bar';
import { RenameDialog } from '@/components/rename-dialog';
import { Button } from '@/components/ui/button';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { useAccessLevel } from '@/hooks/use-access-level';
import { useFetchNextKnowledgeListByPage } from '@/hooks/use-knowledge-request';
import { useListTenant } from '@/hooks/use-user-setting-request';
import { Routes } from '@/routes';
import { useQueryClient } from '@tanstack/react-query';
import { pick } from 'lodash';
import { Plus } from 'lucide-react';
import { useCallback, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';
import { TenantRole } from '../user-setting/constants';
import { DatasetCard } from './dataset-card';
import { DatasetCreatingDialog } from './dataset-creating-dialog';
import { useSaveKnowledge } from './hooks';
import { useRenameDataset } from './use-rename-dataset';
import { useSelectOwners } from './use-select-owners';

export default function Datasets() {
  const { t } = useTranslation();
  const { isKbOnly } = useAccessLevel();
  const { data: tenantData } = useListTenant();
  const {
    visible,
    hideModal,
    showModal,
    onCreateOk,
    loading: creatingLoading,
  } = useSaveKnowledge();

  const {
    kbs,
    total_datasets,
    pagination,
    setPagination,
    handleInputChange,
    searchString,
    filterValue,
    handleFilterSubmit,
  } = useFetchNextKnowledgeListByPage();

  const owners = useSelectOwners();

  // kb_only 看不到团队知识库时的引导提示
  const kbOnlyTeamHint = useMemo(() => {
    if (!isKbOnly) return null;
    const hasInvite = tenantData?.some((x) => x.role === TenantRole.Invite);
    const hasJoined = tenantData?.some((x) => x.role === TenantRole.Normal);
    if (hasInvite) {
      return '你有待接受的团队邀请。请到「设置 → 团队」接受后，才能看到管理员共享的知识库。';
    }
    if (!hasJoined) {
      return '尚未加入任何团队。请让管理员在「设置 → 团队」邀请你，并将知识库权限设为「团队」。';
    }
    return '已加入团队但仍看不到知识库时，请确认管理员已将知识库权限设为「团队」。';
  }, [isKbOnly, tenantData]);

  const {
    datasetRenameLoading,
    initialDatasetName,
    onDatasetRenameOk,
    datasetRenameVisible,
    hideDatasetRenameModal,
    showDatasetRenameModal,
  } = useRenameDataset();

  const handlePageChange = useCallback(
    (page: number, pageSize?: number) => {
      setPagination({ page, pageSize });
    },
    [setPagination],
  );
  const [searchUrl, setSearchUrl] = useSearchParams();
  const isCreate = searchUrl.get('isCreate') === 'true';
  const queryClient = useQueryClient();
  useEffect(() => {
    // kb_only 禁止创建知识库
    if (isCreate && !isKbOnly) {
      queryClient.invalidateQueries({ queryKey: ['tenantInfo'] });
      showModal();
      searchUrl.delete('isCreate');
      setSearchUrl(searchUrl);
    } else if (isCreate && isKbOnly) {
      searchUrl.delete('isCreate');
      setSearchUrl(searchUrl);
    }
  }, [isCreate, isKbOnly, showModal, searchUrl, setSearchUrl, queryClient]);

  return (
    <>
      {kbs?.length || searchString ? (
        <article
          className="size-full min-w-0 flex flex-col"
          data-testid="datasets-list"
        >
          <header className="mb-4 min-w-0 px-5 pt-8">
            <ListFilterBar
              title={t('header.dataset')}
              searchString={searchString}
              onSearchChange={handleInputChange}
              value={filterValue}
              filters={owners}
              onChange={handleFilterSubmit}
              icon={'datasets'}
            >
              {!isKbOnly && (
                <Button onClick={showModal}>
                  <Plus className="size-[1em]" />
                  {t('knowledgeList.createKnowledgeBase')}
                </Button>
              )}
            </ListFilterBar>
          </header>

          {kbs?.length ? (
            <>
              <CardContainer className="flex-1 overflow-auto px-5">
                {kbs.map((dataset) => (
                  <DatasetCard
                    dataset={dataset}
                    key={dataset.id}
                    showDatasetRenameModal={showDatasetRenameModal}
                  />
                ))}
              </CardContainer>

              <footer className="mt-4 px-5 pb-5">
                <RAGFlowPagination
                  {...pick(pagination, 'current', 'pageSize')}
                  total={total_datasets}
                  onChange={handlePageChange}
                />
              </footer>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <EmptyAppCard
                showIcon
                size="large"
                className="w-[480px] p-14"
                isSearch
                type={EmptyCardType.Dataset}
                onClick={isKbOnly ? undefined : () => showModal()}
              />
            </div>
          )}
        </article>
      ) : (
        <article
          className="size-full flex flex-col items-center justify-center gap-4 px-5"
          data-testid="datasets-list"
        >
          {kbOnlyTeamHint && (
            <p className="max-w-lg text-center text-sm text-text-secondary">
              {kbOnlyTeamHint}{' '}
              <Link
                className="text-accent-primary underline"
                to={`${Routes.UserSetting}${Routes.Team}`}
              >
                前往团队
              </Link>
            </p>
          )}
          <EmptyAppCard
            showIcon
            size="large"
            className="w-[480px] p-14"
            type={EmptyCardType.Dataset}
            onClick={isKbOnly ? undefined : () => showModal()}
          />
        </article>
      )}
      {!isKbOnly && visible && (
        <DatasetCreatingDialog
          hideModal={hideModal}
          onOk={onCreateOk}
          loading={creatingLoading}
        ></DatasetCreatingDialog>
      )}
      {!isKbOnly && datasetRenameVisible && (
        <RenameDialog
          hideModal={hideDatasetRenameModal}
          onOk={onDatasetRenameOk}
          initialName={initialDatasetName}
          loading={datasetRenameLoading}
        ></RenameDialog>
      )}
    </>
  );
}
