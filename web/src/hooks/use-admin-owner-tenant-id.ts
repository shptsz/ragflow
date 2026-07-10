import { useAccessLevel } from '@/hooks/use-access-level';
import { useListTenant } from '@/hooks/use-user-setting-request';
import { useMemo } from 'react';
import { TenantRole } from '@/pages/user-setting/constants';

/**
 * kb_only 成员创建/配置知识库时，使用已加入团队所有者的租户 ID 拉取模型。
 * 非 kb_only 返回 undefined（走自身租户）。
 */
export function useAdminOwnerTenantId(): string | undefined {
  const { isKbOnly } = useAccessLevel();
  const { data: tenantData } = useListTenant();

  return useMemo(() => {
    if (!isKbOnly) return undefined;
    const joined = tenantData?.find((x) => x.role === TenantRole.Normal);
    return joined?.tenant_id;
  }, [isKbOnly, tenantData]);
}
