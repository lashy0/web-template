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

import { deletePak, updatePakActive, updatePakArchived, type Pak } from '@/features/paks/paks-api'
import useCustomToast from '@/hooks/useCustomToast'

type Action = 'activate' | 'archive' | 'delete' | 'deactivate' | 'restore'

const content: Record<
  Action,
  Readonly<{
    button: string
    description: (code: string) => string
    success: string
    title: string
  }>
> = {
  activate: {
    button: 'Активировать',
    description: (code) => `ПАК «${code}» снова будет разрешён к работе.`,
    success: 'ПАК активирован',
    title: 'Активировать ПАК?',
  },
  archive: {
    button: 'Архивировать',
    description: (code) =>
      `ПАК «${code}» будет скрыт из текущего списка. Архивация не связана с доступностью комплекса.`,
    success: 'ПАК архивирован',
    title: 'Архивировать ПАК?',
  },
  deactivate: {
    button: 'Отключить',
    description: (code) =>
      `Работа ПАК «${code}» будет запрещена, но он останется в текущем списке.`,
    success: 'ПАК отключён',
    title: 'Отключить ПАК?',
  },
  delete: {
    button: 'Удалить',
    description: (code) =>
      `ПАК «${code}» будет удалён без возможности восстановления. Записи аудита сохранятся.`,
    success: 'ПАК удалён',
    title: 'Удалить ПАК навсегда?',
  },
  restore: {
    button: 'Восстановить',
    description: (code) =>
      `ПАК «${code}» будет возвращён в текущий список. Его состояние доступности не изменится.`,
    success: 'ПАК восстановлен',
    title: 'Восстановить ПАК?',
  },
}

export function PakConfirmation({
  action,
  onOpenChange,
  onSuccess,
  open,
  pak,
}: Readonly<{
  action: Action
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  pak: Pak
}>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: async () => {
      if (action === 'archive') await updatePakArchived(pak.id, true)
      else if (action === 'restore') await updatePakArchived(pak.id, false)
      else if (action === 'activate') await updatePakActive(pak.id, true)
      else if (action === 'deactivate') await updatePakActive(pak.id, false)
      else await deletePak(pak.id)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['paks'] })
      close(true)
      onSuccess()
      showSuccessToast(content[action].success, `ПАК «${pak.code}» успешно обработан.`)
    },
    onError: () => showErrorToast('Не удалось выполнить действие с ПАК', 'Попробуйте ещё раз.'),
  })

  function close(force = false) {
    if (!mutation.isPending || force) onOpenChange(false)
  }

  const details = content[action]

  return (
    <Dialog onOpenChange={close} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        <DialogHeader>
          <DialogTitle>{details.title}</DialogTitle>
          <DialogDescription>{details.description(pak.code)}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => close()} variant="outline">
            Отмена
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            variant={action === 'delete' ? 'destructive' : 'default'}
          >
            {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
            {mutation.isPending ? 'Выполнение…' : details.button}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
