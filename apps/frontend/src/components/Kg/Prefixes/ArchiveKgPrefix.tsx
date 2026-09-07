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

import { updateKgPrefixArchived, type KgPrefix } from '@/features/kg/kg-prefixes-api'
import useCustomToast from '@/hooks/useCustomToast'

export function ArchiveKgPrefix({
  onOpenChange,
  open,
  prefix,
}: Readonly<{ onOpenChange: (open: boolean) => void; open: boolean; prefix: KgPrefix }>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const restore = prefix.archivedAt !== null
  const action = restore ? 'Восстановить' : 'Архивировать'
  const mutation = useMutation({
    mutationFn: () => updateKgPrefixArchived(prefix.prefix, !restore),
    onError: () =>
      showErrorToast(`Не удалось ${action.toLowerCase()} префикс`, 'Попробуйте ещё раз.'),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['kg', 'prefixes'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      onOpenChange(false)
      showSuccessToast(
        restore ? 'Префикс восстановлен' : 'Префикс архивирован',
        restore
          ? `Префикс «${prefix.prefix}» возвращён в текущий список.`
          : `Префикс «${prefix.prefix}» больше нельзя использовать для новых партий.`,
      )
    },
  })
  return (
    <Dialog onOpenChange={(next) => !mutation.isPending && onOpenChange(next)} open={open}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{action} префикс?</DialogTitle>
          <DialogDescription>
            {restore
              ? `Префикс «${prefix.prefix}» снова станет доступен для новых партий.`
              : `Префикс «${prefix.prefix}» будет скрыт из текущего списка и недоступен для новых партий.`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            disabled={mutation.isPending}
            onClick={() => onOpenChange(false)}
            variant="outline"
          >
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
