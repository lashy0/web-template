import { useMutation, useQueryClient } from '@tanstack/react-query'
import { completeBatchMutation } from '@web-app/api-client'

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

export function CompleteBatch({
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
  const mutation = useMutation({
    ...completeBatchMutation(),
    onError: () => showErrorToast('Не удалось завершить партию', 'Попробуйте ещё раз.'),
    onSuccess: async (completedBatch) => {
      await invalidateBatchQueries(queryClient)
      onOpenChange(false)
      onSuccess()
      showSuccessToast(
        'Партия завершена',
        `Партия «${completedBatch.name}» переведена в статус «Завершена».`,
      )
    },
  })

  function close(force = false) {
    if (mutation.isPending && !force) return
    onOpenChange(false)
  }

  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : close())} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        <DialogHeader>
          <DialogTitle>Завершить партию?</DialogTitle>
          <DialogDescription>
            Партия «{batch.name}» будет переведена в статус «Завершена». Вернуть её в производство
            будет нельзя.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => close()} variant="outline">
            Отмена
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate({ path: { batch_id: batch.id } })}
            variant="destructive"
          >
            {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
            {mutation.isPending ? 'Завершение…' : 'Завершить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
