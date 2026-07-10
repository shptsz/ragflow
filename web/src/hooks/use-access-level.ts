import { AccessLevel } from '@/constants/access-level';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';

export function useAccessLevel() {
  const { data: userInfo, loading, isError, isFetched, error } =
    useFetchUserInfo();

  // 有真实身份字段才算就绪（空对象不算）
  const isReady = Boolean(userInfo?.id || userInfo?.email);
  const isKbOnly =
    isReady && userInfo?.access_level === AccessLevel.KbOnly;
  const accessLevel = isKbOnly ? AccessLevel.KbOnly : AccessLevel.Full;

  // 仅在「尚未拿到身份」时转圈；后台 refetch 不再挡住整页
  const isLoading = !isReady && !isError && loading;

  return {
    accessLevel,
    isKbOnly,
    isLoading,
    isReady,
    // 请求失败，或请求结束仍无身份
    isError: isError || (isFetched && !isReady && !loading),
    error:
      error ??
      (isFetched && !isReady && !loading
        ? new Error('用户信息为空，请重新登录')
        : null),
    userInfo,
  };
}
