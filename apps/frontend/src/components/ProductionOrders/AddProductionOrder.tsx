import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PlusIcon } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@web-app/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@web-app/ui/components/dialog'
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
  createProductionOrder,
  productionOrderErrorMessage,
  productionOrderQueryKeys,
} from '@/features/production-orders/production-order-api'
import { productionOrderFormSchema } from '@/features/production-orders/production-order-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type CreateProductionOrderForm = Readonly<{ description: string; name: string }>

const initialValues: CreateProductionOrderForm = { description: '', name: '' }
const textLimit = 2000

export function AddProductionOrder() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const form = useForm<CreateProductionOrderForm>({
    defaultValues: initialValues,
    mode: 'onBlur',
    reValidateMode: 'onBlur',
    resolver: zodResolver(productionOrderFormSchema),
  })
  const mutation = useMutation({
    mutationFn: (values: CreateProductionOrderForm) =>
      createProductionOrder({
        description: values.description.trim() || null,
        name: values.name.trim(),
      }),
    onError: (error) =>
      showErrorToast(
        'Не удалось создать производственный заказ',
        productionOrderErrorMessage(error) ?? 'Проверьте данные и попробуйте ещё раз.',
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: productionOrderQueryKeys.all })
      close(true)
      showSuccessToast('Производственный заказ создан')
    },
  })

  function close(force = false) {
    if (mutation.isPending && !force) return
    form.reset(initialValues)
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
        <DialogHeader className="shrink-0 px-4 pt-4">
          <DialogTitle>Новый производственный заказ</DialogTitle>
          <DialogDescription>Укажите название и описание заказа.</DialogDescription>
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
                  <FieldLabel className="cursor-pointer" htmlFor="new-production-order-name">
                    Название
                    <span aria-hidden="true" className="ml-0.5 text-destructive">
                      *
                    </span>
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id="new-production-order-name"
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
                  <FieldLabel className="cursor-pointer" htmlFor="new-production-order-description">
                    Описание
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id="new-production-order-description"
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
            <Button
              disabled={mutation.isPending}
              onClick={() => close()}
              type="button"
              variant="outline"
            >
              Отмена
            </Button>
            <Button disabled={mutation.isPending || !form.formState.isDirty} type="submit">
              {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
              {mutation.isPending ? 'Создание…' : 'Создать'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
