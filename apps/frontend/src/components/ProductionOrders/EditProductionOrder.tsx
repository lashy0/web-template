import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo } from 'react'
import { Controller, useForm } from 'react-hook-form'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@web-app/ui/components/dialog'
import { Button } from '@web-app/ui/components/button'
import { Field, FieldError, FieldGroup, FieldLabel } from '@web-app/ui/components/field'
import { Input } from '@web-app/ui/components/input'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupText,
  InputGroupTextarea,
} from '@web-app/ui/components/input-group'
import { Spinner } from '@web-app/ui/components/spinner'

import {
  productionOrderErrorMessage,
  productionOrderQueryKeys,
  updateProductionOrder,
  type ProductionOrder,
} from '@/features/production-orders/production-order-api'
import { productionOrderFormSchema } from '@/features/production-orders/production-order-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type EditProductionOrderForm = Readonly<{ description: string; name: string }>

const textLimit = 2000

export function EditProductionOrder({
  onOpenChange,
  onSuccess,
  open,
  order,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  order: ProductionOrder
}>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: (values: EditProductionOrderForm) =>
      updateProductionOrder(order.id, {
        description: values.description.trim() || null,
        name: values.name.trim(),
      }),
    onError: (error) =>
      showErrorToast(
        'Не удалось изменить производственный заказ',
        productionOrderErrorMessage(error) ?? 'Проверьте данные и попробуйте ещё раз.',
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: productionOrderQueryKeys.all })
      onOpenChange(false)
      onSuccess()
      showSuccessToast('Производственный заказ изменён')
    },
  })
  const initialValues = useMemo(
    () => ({ description: order.description ?? '', name: order.name }),
    [order.description, order.name],
  )
  const form = useForm<EditProductionOrderForm>({
    defaultValues: initialValues,
    mode: 'onBlur',
    reValidateMode: 'onBlur',
    resolver: zodResolver(productionOrderFormSchema),
  })
  useEffect(() => {
    if (open) form.reset(initialValues)
  }, [form, initialValues, open])

  function close() {
    if (!mutation.isPending) onOpenChange(false)
  }

  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : close())} open={open}>
      <DialogContent
        className="flex max-h-[calc(100dvh-2rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg"
        showCloseButton={!mutation.isPending}
      >
        <DialogHeader className="shrink-0 px-4 pt-4">
          <DialogTitle>Изменить производственный заказ</DialogTitle>
          <DialogDescription>Измените название или описание заказа.</DialogDescription>
        </DialogHeader>
        <form
          autoComplete="off"
          className="flex min-h-0 flex-1 flex-col"
          noValidate
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
        >
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <Controller
              control={form.control}
              name="name"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel
                    className="cursor-pointer"
                    htmlFor={`production-order-${order.id}-name`}
                  >
                    Название
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id={`production-order-${order.id}-name`}
                    required
                  />
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="description"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel
                    className="cursor-pointer"
                    htmlFor={`production-order-${order.id}-description`}
                  >
                    Описание
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id={`production-order-${order.id}-description`}
                      maxLength={textLimit}
                    />
                    <InputGroupAddon align="block-end">
                      <InputGroupText className="text-xs font-normal tabular-nums">
                        {field.value.length} / {textLimit}
                      </InputGroupText>
                    </InputGroupAddon>
                  </InputGroup>
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
          </FieldGroup>
          <div className="flex shrink-0 justify-end gap-2 px-4 py-4">
            <Button disabled={mutation.isPending} onClick={close} type="button" variant="outline">
              Отмена
            </Button>
            <Button disabled={mutation.isPending || !form.formState.isDirty} type="submit">
              {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
              {mutation.isPending ? 'Сохранение…' : 'Сохранить'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
