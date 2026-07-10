import { Modal } from '@/components/ui/modal/modal';
import DOMPurify from 'dompurify';
import { isEmpty } from 'lodash';
import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useAccessLevel } from './use-access-level';
import { useNavigatePage } from './logic-hooks/navigate-hooks';

export const useWarnEmptyModel = (
  showEmptyModelWarn: boolean,
  embdId?: string,
  llmId?: string,
  loading?: boolean,
) => {
  const { t } = useTranslation();
  const warnedRef = useRef(false);
  const { navigateToModelSetting } = useNavigatePage();
  const { isKbOnly } = useAccessLevel();

  useEffect(() => {
    // kb_only 不能配置模型，改用管理员已配模型，勿弹「去模型设置」提醒
    if (isKbOnly) {
      return;
    }
    if (
      showEmptyModelWarn &&
      !warnedRef.current &&
      !loading &&
      (isEmpty(embdId) || isEmpty(llmId)) &&
      typeof embdId === 'string' &&
      typeof llmId === 'string'
    ) {
      warnedRef.current = true;
      Modal.warning({
        title: t('common.warn'),
        content: (
          <div
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(t('setting.modelProvidersWarn')),
            }}
          ></div>
        ),
        closable: false,
        showCancel: false,
        onOk() {
          navigateToModelSetting();
        },
      });
    }
  }, [
    showEmptyModelWarn,
    embdId,
    llmId,
    loading,
    navigateToModelSetting,
    t,
    isKbOnly,
  ]);
};
