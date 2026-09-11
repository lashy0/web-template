import { useMutation, useQueryClient } from '@tanstack/react-query'
import { TriangleAlertIcon } from 'lucide-react'
import { useState } from 'react'

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
  batchErrorCode,
  batchErrorMessage,
  batchQueryKeys,
  deleteBatch,
  type Batch,
} from '@/features/batches/batches-api'
import useCustomToast from '@/hooks/useCustomToast'

export function DeleteBatch({
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
  const [blockedByProductionActivity, setBlockedByProductionActivity] = useState(false)
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => deleteBatch(batch.id),
    onError: (error) => {
      if (batchErrorCode(error) === 'batch_cannot_be_deleted') {
        setBlockedByProductionActivity(true)
        return
      }
      showErrorToast('Не удалось удалить партию', batchErrorMessage(error) ?? 'Попробуйте ещё раз.')
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: batchQueryKeys.all })
      onOpenChange(false)
      onSuccess()
      showSuccessToast('Партия удалена', `Партия «${batch.name}» удалена навсегда.`)
    },
  })
  function close(force = false) {
    if (mutation.isPending && !force) return
    setBlockedByProductionActivity(false)
    onOpenChange(false)
  }

  const hasProductionActivity = !batch.canDelete || blockedByProductionActivity

  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : close())} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        {hasProductionActivity ? (
          <DeleteWarning batch={batch} onOpenChange={close} />
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Удалить партию?</DialogTitle>
              <DialogDescription>
                Партия «{batch.name}» будет удалена без возможности восстановления.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button disabled={mutation.isPending} onClick={() => close()} variant="outline">
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
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

function DeleteWarning({
  batch,
  onOpenChange,
}: Readonly<{
  batch: Batch
  onOpenChange: (force?: boolean) => void
}>) {
  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <TriangleAlertIcon aria-hidden="true" className="size-5 text-amber-500" />
          Нельзя удалить партию
        </DialogTitle>
        <DialogDescription>
          В партии «{batch.name}» есть производственные операции.
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button onClick={() => onOpenChange()} type="button" variant="outline">
          Отмена
        </Button>
      </DialogFooter>
    </>
  )
}
