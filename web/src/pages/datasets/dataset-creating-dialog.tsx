import { DataFlowSelect } from '@/components/data-pipeline-select';
import { ButtonLoading } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { FormLayout } from '@/constants/form';
import { ParseType } from '@/constants/knowledge';
import {
  useFetchAllAddedModels,
  useFetchDefaultModelDictionary,
} from '@/hooks/use-llm-request';
import { IModalProps } from '@/interfaces/common';
import { buildModelValue, getRealModelName } from '@/utils/llm-util';
import { zodResolver } from '@hookform/resolvers/zod';
import { omit } from 'lodash';
import { useEffect } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import {
  ChunkMethodItem,
  EmbeddingModelItem,
  ParseTypeItem,
} from '../dataset/dataset-setting/configuration/common-item';

const FormId = 'dataset-creating-form';

const ChunkMethodName = 'chunk_method';

export function InputForm({ onOk }: IModalProps<any>) {
  const { t } = useTranslation();
  const { data: addedModels } = useFetchAllAddedModels('embedding');
  const defaultModelDictionary = useFetchDefaultModelDictionary();

  const defaultEmbd =
    defaultModelDictionary?.embd_id ||
    (addedModels?.[0]
      ? buildModelValue({
          model_name: getRealModelName(addedModels[0].name),
          model_instance: addedModels[0].instance_name,
          model_provider: addedModels[0].provider_name,
        })
      : '');

  const FormSchema = z
    .object({
      name: z
        .string()
        .min(1, {
          message: t('knowledgeList.namePlaceholder'),
        })
        .trim(),
      parseType: z.nativeEnum(ParseType).optional(),
      embedding_model: z
        .string()
        .min(1, {
          message: t('knowledgeConfiguration.embeddingModelPlaceholder'),
        })
        .trim(),
      [ChunkMethodName]: z.string().optional(),
      pipeline_id: z.string().optional(),
    })
    .superRefine((data, ctx) => {
      if (
        data.parseType === ParseType.BuiltIn &&
        (!data[ChunkMethodName] || data[ChunkMethodName].trim() === '')
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('knowledgeList.parserRequired'),
          path: [ChunkMethodName],
        });
      }
      if (data.parseType === ParseType.Pipeline && !data.pipeline_id) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('knowledgeList.dataFlowRequired'),
          path: ['pipeline_id'],
        });
      }
    });

  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      name: '',
      parseType: ParseType.BuiltIn,
      [ChunkMethodName]: '',
      embedding_model: defaultEmbd || defaultModelDictionary?.embd_id,
    },
  });

  const parseType = useWatch({
    control: form.control,
    name: 'parseType',
  });

  function onSubmit(data: z.infer<typeof FormSchema>) {
    const nextData =
      parseType === ParseType.BuiltIn ? data : omit(data, ChunkMethodName);
    // 若误选了 model_id（无 @），转成后端要求的复合格式
    const embd = nextData.embedding_model;
    if (embd && !embd.includes('@') && addedModels?.length) {
      const matched = addedModels.find((m) => m.model_id === embd);
      if (matched) {
        nextData.embedding_model = buildModelValue({
          model_name: getRealModelName(matched.name),
          model_instance: matched.instance_name,
          model_provider: matched.provider_name,
        });
      }
    }
    onOk?.(nextData);
  }

  useEffect(() => {
    if (parseType === ParseType.BuiltIn) {
      form.setValue('pipeline_id', '');
    }
  }, [parseType, form]);

  useEffect(() => {
    const next = defaultEmbd || defaultModelDictionary?.embd_id;
    if (next) {
      form.setValue('embedding_model', next);
    }
  }, [defaultEmbd, defaultModelDictionary?.embd_id, form]);

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit, (errors) => {
          console.warn(errors);
        })}
        className="space-y-6"
        id={FormId}
      >
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem className="space-y-1">
              <FormLabel required>{t('knowledgeList.name')}</FormLabel>
              <FormControl>
                <Input
                  placeholder={t('knowledgeList.namePlaceholder')}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <EmbeddingModelItem line={2} isEdit={false} />
        <ParseTypeItem />
        {parseType === ParseType.BuiltIn && (
          <ChunkMethodItem name={ChunkMethodName}></ChunkMethodItem>
        )}
        {parseType === ParseType.Pipeline && (
          <DataFlowSelect
            isMult={false}
            showToDataPipeline={true}
            formFieldName="pipeline_id"
            layout={FormLayout.Vertical}
          />
        )}
      </form>
    </Form>
  );
}

export function DatasetCreatingDialog({
  visible,
  hideModal,
  loading,
  onOk,
}: IModalProps<any>) {
  const { t } = useTranslation();

  return (
    <Dialog open onOpenChange={hideModal}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('knowledgeList.createKnowledgeBase')}</DialogTitle>
          <DialogDescription className="sr-only" />
        </DialogHeader>
        <InputForm onOk={onOk}></InputForm>
        <DialogFooter>
          <ButtonLoading type="submit" form={FormId} loading={loading}>
            {t('common.save')}
          </ButtonLoading>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
