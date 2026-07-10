/*
 *  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

import { ModelTreeSelect, ModelTypeMap } from '@/components/model-tree-select';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { FieldToModelType } from '@/constants/llm';
import { useTranslate } from '@/hooks/common-hooks';
import {
  useFetchAllAddedModels,
  useFetchDefaultModelDictionary,
  useSetDefaultModel,
} from '@/hooks/use-llm-request';
import { getRealModelName, parseModelValue, buildModelValue } from '@/utils/llm-util';
import { CircleQuestionMark } from 'lucide-react';
import { useCallback, useMemo } from 'react';

interface ModelFieldItemProps {
  id: string;
  label: string;
  value: string;
  tooltip?: string;
  isRequired?: boolean;
  onChange: (id: string, value: string) => void;
}

function ModelFieldItem({
  label,
  value,
  tooltip,
  id,
  isRequired,
  onChange,
}: ModelFieldItemProps) {
  const { t } = useTranslate('setting');

  return (
    <div className="flex gap-3 items-center">
      <label className="block text-sm font-normal text-text-secondary w-1/4 max-w-[150px]">
        {isRequired && <span className="text-state-error">*</span>}
        {label}
        {tooltip && (
          <Tooltip>
            <TooltipContent>{tooltip}</TooltipContent>
            <TooltipTrigger>
              <CircleQuestionMark
                size={12}
                className="ml-1 text-text-secondary text-xs"
              />
            </TooltipTrigger>
          </Tooltip>
        )}
      </label>
      <div className="w-3/4 flex-1">
        <ModelTreeSelect
          modelTypes={ModelTypeMap[id as keyof typeof ModelTypeMap] ?? ['chat']}
          value={value}
          onChange={(val) => onChange(id, val)}
          placeholder={t('selectModelPlaceholder')}
          showSearch
          allowClear={id !== 'llm_id'}
        />
      </div>
    </div>
  );
}

function SystemSetting() {
  const { t } = useTranslate('setting');
  const defaultModelDictionary = useFetchDefaultModelDictionary();
  const { setDefaultModel } = useSetDefaultModel();
  // ModelTreeSelect 的 onChange 传的是 model_id，不是 name@instance@provider
  const { data: allAddedModels } = useFetchAllAddedModels();

  const handleFieldChange = useCallback(
    async (field: string, value: string) => {
      const modelType = FieldToModelType[field];
      if (!modelType) return;

      if (!value) {
        await setDefaultModel({
          model_provider: '',
          model_instance: '',
          model_name: '',
          model_type: modelType,
        });
        return;
      }

      // 优先按 model_id 解析；旧后端无 model_id 时树节点 id 就是 name@instance@provider
      const added =
        allAddedModels.find((m) => m.model_id && m.model_id === value) ||
        allAddedModels.find((m) => {
          const legacy = buildModelValue({
            model_name: getRealModelName(m.name),
            model_instance: m.instance_name,
            model_provider: m.provider_name,
          });
          return legacy === value;
        });
      if (added) {
        await setDefaultModel({
          model_provider: added.provider_name,
          model_instance: added.instance_name,
          model_name: getRealModelName(added.name),
          model_type: modelType,
        });
        return;
      }

      // 兼容旧的 name@instance@provider 字符串
      const parsed = parseModelValue(value);
      if (!parsed) return;
      await setDefaultModel({ ...parsed, model_type: modelType });
    },
    [allAddedModels, setDefaultModel],
  );

  const llmList = useMemo(() => {
    return [
      {
        id: 'llm_id',
        label: t('chatModel'),
        isRequired: true,
        value: defaultModelDictionary.llm_id,
        tooltip: t('chatModelTip'),
      },
      {
        id: 'embd_id',
        label: t('embeddingModel'),
        value: defaultModelDictionary.embd_id,
        tooltip: t('embeddingModelTip'),
      },
      {
        id: 'img2txt_id',
        label: t('img2txtModel'),
        value: defaultModelDictionary.img2txt_id,
        tooltip: t('img2txtModelTip'),
      },
      {
        id: 'asr_id',
        label: t('sequence2txtModel'),
        value: defaultModelDictionary.asr_id,
        tooltip: t('sequence2txtModelTip'),
      },
      {
        id: 'rerank_id',
        label: t('rerankModel'),
        value: defaultModelDictionary.rerank_id,
        tooltip: t('rerankModelTip'),
      },
      {
        id: 'tts_id',
        label: t('ttsModel'),
        value: defaultModelDictionary.tts_id,
        tooltip: t('ttsModelTip'),
      },
    ];
  }, [defaultModelDictionary, t]);

  return (
    <article className="rounded-lg w-full">
      <header className="py-5 px-10">
        <h2 className="text-2xl font-medium text-text-primary">
          {t('systemModelSettings')}
        </h2>
        <p className="mt-1 text-sm text-text-secondary ">
          {t('systemModelDescription')}
        </p>
      </header>

      <div className="px-10 py-6 space-y-6 max-h-[70vh] overflow-y-auto ">
        {llmList.map((item) => (
          <ModelFieldItem
            key={item.id}
            {...item}
            onChange={handleFieldChange}
          />
        ))}
      </div>
    </article>
  );
}

export default SystemSetting;
