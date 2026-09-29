import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteBatchMutation } from '@web-app/api-client'
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
  invalidateBatchQueries,
  isBatchEditWindowExpiredError,
  isBatchInUseError,
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
    ...deleteBatchMutation(),
    onError: (error) => {
      if (isBatchInUseError(error)) {
        setBlockedByProductionActivity(true)
        return
      }
      showErrorToast(
        'Не удалось удалить партию',
        isBatchEditWindowExpiredError(error)
          ? 'Партию можно удалить только в течение часа после создания. Архивируйте её.'
          : 'Попробуйте ещё раз.',
      )
    },
    onSuccess: async () => {
      await invalidateBatchQueries(queryClient)
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

  const hasProductionActivity = blockedByProductionActivity

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
                onClick={() => mutation.mutate({ path: { batch_id: batch.id } })}
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
          По партии «{batch.name}» уже были приёмки, отгрузки, проверки или упаковка. Архивируйте
          её, чтобы скрыть из списка.
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
