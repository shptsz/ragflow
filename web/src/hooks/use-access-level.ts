import { AccessLevel } from '@/constants/access-level';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';

export function useAccessLevel() {
  const { data: userInfo } = useFetchUserInfo();
  const accessLevel =
    userInfo?.access_level === AccessLevel.KbOnly
      ? AccessLevel.KbOnly
      : AccessLevel.Full;
  return {
    accessLevel,
    isKbOnly: accessLevel === AccessLevel.KbOnly,
    userInfo,
  };
}
