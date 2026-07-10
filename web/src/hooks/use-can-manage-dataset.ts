import { useAccessLevel } from '@/hooks/use-access-level';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { IDataset } from '@/interfaces/database/dataset';

/**
 * 是否可管理知识库本体（重命名、删除、配置）。
 * 仅知识库所属租户所有者可管理；团队共享库对成员只读配置。
 */
export function useCanManageDataset(
  dataset?: Pick<IDataset, 'tenant_id'> | null,
) {
  const { data: userInfo } = useFetchUserInfo();
  const { isKbOnly } = useAccessLevel();

  const userId = userInfo?.id;
  const isOwner = Boolean(userId && dataset?.tenant_id === userId);
  // kb_only 一律不可管理知识库本体
  const canManage = !isKbOnly && isOwner;

  return { canManage, isOwner, isKbOnly };
}
