import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeftIcon, ArrowRightIcon, PlusIcon } from 'lucide-react'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'

import { Button } from '@web-app/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@web-app/ui/components/dialog'
import { Spinner } from '@web-app/ui/components/spinner'

import { BatchConfigurationStep } from './batch-form/BatchConfigurationStep'
import { BatchParametersStep } from './batch-form/BatchParametersStep'
import { BatchStepIndicator } from './batch-form/BatchStepIndicator'
import { useBatchFormOptions } from './batch-form/useBatchFormOptions'
import {
  batchStepOneFields,
  initialBatchFormValues,
  type CreateBatchForm,
  type FormStep,
} from './batch-form/types'

import {
  batchErrorMessage,
  batchQueryKeys,
  createBatch,
  previewDevEuiRange,
} from '@/features/batches/batches-api'
import { createBatchFormSchema } from '@/features/batches/batch-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

export function AddBatch() {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<FormStep>(1)
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const form = useForm<CreateBatchForm>({
    defaultValues: initialBatchFormValues,
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: zodResolver(createBatchFormSchema),
  })
  const plannedQty = Number(useWatch({ control: form.control, name: 'plannedQty' }))
  const selectedPrefix = useWatch({ control: form.control, name: 'devEuiPrefix' })
  const { prefixes, versions, orders } = useBatchFormOptions(open)
  const devEuiRange = useQuery({
    enabled: open && step === 2 && selectedPrefix.length > 0 && plannedQty > 0,
    queryFn: () => previewDevEuiRange(selectedPrefix, plannedQty),
    queryKey: batchQueryKeys.devEuiRange(selectedPrefix, plannedQty),
  })
  const mutation = useMutation({
    mutationFn: (values: CreateBatchForm) =>
      createBatch({
        day_plan_qty: Number(values.dayPlanQty),
        description: values.description.trim() || null,
        dev_eui_prefix: values.devEuiPrefix,
        kg_version_id: values.kgVersionId,
        lorawan_config: {
          activation_type: values.activationType,
          lorawan_version: values.lorawanVersion,
        },
        name: values.name.trim(),
        planned_qty: Number(values.plannedQty),
        production_order_id: values.productionOrderId || null,
      }),
    onError: (error) =>
      showErrorToast(
        'Не удалось создать партию',
        batchErrorMessage(error) ?? 'Проверьте данные и попробуйте ещё раз.',
      ),
    onSuccess: async (batch) => {
      await queryClient.invalidateQueries({ queryKey: batchQueryKeys.all })
      close(true)
      showSuccessToast('Партия создана', `Партия «${batch.name}» успешно добавлена.`)
    },
  })

  async function goToConfiguration() {
    const valid = await form.trigger(batchStepOneFields, { shouldFocus: true })
    if (valid) {
      setStep(2)
    }
  }

  function close(force = false) {
    if (mutation.isPending && !force) return
    form.reset(initialBatchFormValues)
    setStep(1)
    setOpen(false)
  }

  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? setOpen(true) : close())} open={open}>
      <DialogTrigger render={<Button className="cursor-pointer self-start sm:self-auto" />}>
        <PlusIcon data-icon="inline-start" />
        Добавить
      </DialogTrigger>
      <DialogContent
        className="flex max-h-[calc(100dvh-2rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg"
        showCloseButton={!mutation.isPending}
      >
        <form
          autoComplete="off"
          className="flex min-h-0 flex-1 flex-col"
          noValidate
          onSubmit={(event) => {
            event.preventDefault()
            if (step === 1) {
              void goToConfiguration()
              return
            }
            void form.handleSubmit((values) => mutation.mutate(values))()
          }}
        >
          <DialogHeader className="shrink-0 px-4 pt-4">
            <DialogTitle>Новая партия</DialogTitle>
          </DialogHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <BatchStepIndicator activeStep={step} />
            <div key={step}>
              {step === 1 ? (
                <BatchParametersStep control={form.control} orders={orders} />
              ) : (
                <BatchConfigurationStep
                  control={form.control}
                  plannedQty={plannedQty}
                  prefixes={prefixes}
                  range={devEuiRange.data}
                  rangeLoading={devEuiRange.isFetching}
                  selectedPrefix={selectedPrefix}
                  versions={versions}
                />
              )}
            </div>
          </div>
          <DialogFooter className="mx-0 mb-0 shrink-0 gap-2 rounded-b-xl px-4 py-4">
            {step === 1 ? (
              <Button
                disabled={mutation.isPending}
                onClick={() => close()}
                type="button"
                variant="outline"
              >
                Отмена
              </Button>
            ) : (
              <Button
                disabled={mutation.isPending}
                onClick={() => setStep(1)}
                type="button"
                variant="outline"
              >
                <ArrowLeftIcon data-icon="inline-start" />
                Назад
              </Button>
            )}
            <Button disabled={mutation.isPending} type="submit">
              {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
              {step === 1 ? 'Далее' : mutation.isPending ? 'Создание…' : 'Создать партию'}
              {step === 1 ? <ArrowRightIcon data-icon="inline-end" /> : null}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
