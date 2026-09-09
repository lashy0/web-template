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
  productionOrderErrorMessage,
  productionOrderQueryKeys,
  updateProductionOrderArchived,
  type ProductionOrder,
} from '@/features/production-orders/production-order-api'
import useCustomToast from '@/hooks/useCustomToast'

export function ArchiveStatusProductionOrder({
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
  const restore = order.archivedAt !== null
  const action = restore ? 'Восстановить' : 'Архивировать'
  const mutation = useMutation({
    mutationFn: () => updateProductionOrderArchived(order.id, !restore),
    onError: (error) =>
      showErrorToast(
        `Не удалось ${action.toLowerCase()} производственный заказ`,
        productionOrderErrorMessage(error) ?? 'Попробуйте ещё раз.',
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: productionOrderQueryKeys.all })
      onOpenChange(false)
      onSuccess()
      showSuccessToast(
        restore ? 'Производственный заказ восстановлен' : 'Производственный заказ архивирован',
      )
    },
  })

  function close() {
    if (!mutation.isPending) onOpenChange(false)
  }

  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : close())} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        <DialogHeader>
          <DialogTitle>{action} производственный заказ?</DialogTitle>
          <DialogDescription>
            {restore
              ? `Заказ «${order.name}» будет возвращён в текущий список.`
              : `Заказ «${order.name}» будет скрыт из текущего списка.`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={close} variant="outline">
            Отмена
          </Button>
          <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
            {mutation.isPending ? `${action}…` : action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
