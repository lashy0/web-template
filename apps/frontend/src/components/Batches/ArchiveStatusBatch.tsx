import { useMutation, useQueryClient } from '@tanstack/react-query'
import { archiveBatchMutation, restoreBatchMutation } from '@web-app/api-client'

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

import { invalidateBatchQueries, type Batch } from '@/features/batches/batches-api'
import useCustomToast from '@/hooks/useCustomToast'

export function ArchiveStatusBatch({
  batch,
  onOpenChange,
  onSuccess,
  open,
}: Readonly<{
  batch: Batch
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
}>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const restore = batch.archivedAt !== null
  const action = restore ? 'Восстановить' : 'Архивировать'
  const mutation = useMutation({
    ...(restore ? restoreBatchMutation() : archiveBatchMutation()),
    onError: () =>
      showErrorToast(`Не удалось ${action.toLowerCase()} партию`, 'Попробуйте ещё раз.'),
    onSuccess: async () => {
      await invalidateBatchQueries(queryClient)
      onOpenChange(false)
      onSuccess()
      showSuccessToast(
        restore ? 'Партия восстановлена' : 'Партия архивирована',
        restore
          ? `Партия «${batch.name}» возвращена из архива.`
          : `Партия «${batch.name}» перемещена в архив.`,
      )
    },
  })
  const close = () => {
    if (!mutation.isPending) onOpenChange(false)
  }
  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : close())} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        <DialogHeader>
          <DialogTitle>{action} партию?</DialogTitle>
          <DialogDescription>
            {restore
              ? `Партия «${batch.name}» будет возвращена в текущий список.`
              : `Партия «${batch.name}» будет скрыта из текущего списка.`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={close} variant="outline">
            Отмена
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate({ path: { batch_id: batch.id } })}
          >
            {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
            {mutation.isPending ? `${action}…` : action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
