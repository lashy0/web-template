import { useMutation, useQueryClient } from '@tanstack/react-query'

import { Button } from '@web-app/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@web-app/ui/components/dialog'
import { Spinner } from '@web-app/ui/components/spinner'

import {
  deleteProductionOrder,
  productionOrderErrorCode,
  productionOrderErrorMessage,
  productionOrderQueryKeys,
  type ProductionOrder,
} from '@/features/production-orders/production-order-api'
import useCustomToast from '@/hooks/useCustomToast'

export function DeleteProductionOrder({
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
  const { showErrorToast, showSuccessToast, showWarningToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => deleteProductionOrder(order.id),
    onError: (error) => {
      if (productionOrderErrorCode(error) === 'production_order_cannot_be_deleted') {
        onOpenChange(false)
        showWarningToast('Невозможно удалить производственный заказ: в нём есть партии.')
        return
      }
      showErrorToast(
        'Не удалось удалить производственный заказ',
        productionOrderErrorMessage(error) ?? 'Попробуйте ещё раз.',
      )
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: productionOrderQueryKeys.all })
      onOpenChange(false)
      onSuccess()
      showSuccessToast('Производственный заказ удалён')
    },
  })

  function close() {
    if (!mutation.isPending) onOpenChange(false)
  }

  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : close())} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        <DialogHeader>
          <DialogTitle>Удалить производственный заказ?</DialogTitle>
          <DialogDescription>
            Заказ «{order.name}» будет удалён без возможности восстановления.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={close} variant="outline">
            Отмена
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            variant="destructive"
          >
            {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
            {mutation.isPending ? 'Удаление…' : 'Удалить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
