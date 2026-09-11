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
  batchErrorMessage,
  batchQueryKeys,
  completeBatch,
  type Batch,
} from '@/features/batches/batches-api'
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
    mutationFn: () => completeBatch(batch.id),
    onError: (error) =>
      showErrorToast(
        'Не удалось завершить партию',
        batchErrorMessage(error) ?? 'Попробуйте ещё раз.',
      ),
    onSuccess: async (completedBatch) => {
      await queryClient.invalidateQueries({ queryKey: batchQueryKeys.all })
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
            Партия «{batch.name}» будет переведена в статус «Завершена». Вернуть её в
            производство будет нельзя.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => close()} variant="outline">
            Отмена
          </Button>
          <Button disabled={mutation.isPending} onClick={() => mutation.mutate()} variant="destructive">
            {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
            {mutation.isPending ? 'Завершение…' : 'Завершить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
