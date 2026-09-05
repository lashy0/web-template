import { useMutation } from '@tanstack/react-query'
import { CheckIcon, CopyIcon, EyeIcon, EyeOffIcon, RotateCcwIcon } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'

import { Button } from '@web-app/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@web-app/ui/components/dialog'
import { Spinner } from '@web-app/ui/components/spinner'

import {
  getPakAccessKey,
  pakKindLabels,
  rotatePakAccessKey,
  type Pak,
} from '@/features/paks/paks-api'
import useCustomToast from '@/hooks/useCustomToast'

type CopiedValue = 'accessKey' | 'clientId' | null

export function ViewPakAccessKey({
  onOpenChange,
  open,
  pak,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  open: boolean
  pak: Pak
}>) {
  const requestedForOpen = useRef(false)
  const copiedTimeout = useRef<number | null>(null)
  const [accessKey, setAccessKey] = useState<string | null>(null)
  const [copied, setCopied] = useState<CopiedValue>(null)
  const [isAccessKeyVisible, setIsAccessKeyVisible] = useState(false)
  const [isRotationConfirmationVisible, setIsRotationConfirmationVisible] = useState(false)
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const accessKeyMutation = useMutation({
    mutationFn: () => getPakAccessKey(pak.id),
    onError: () => {
      showErrorToast('Не удалось получить ключ доступа', 'Попробуйте ещё раз.')
    },
    onSuccess: setAccessKey,
  })
  const rotateMutation = useMutation({
    mutationFn: () => rotatePakAccessKey(pak.id),
    onError: () => showErrorToast('Не удалось ротировать ключ доступа', 'Попробуйте ещё раз.'),
    onSuccess: (nextAccessKey) => {
      setAccessKey(nextAccessKey)
      setIsAccessKeyVisible(false)
      setIsRotationConfirmationVisible(false)
      void copy(nextAccessKey, 'accessKey')
      showSuccessToast('Ключ доступа обновлён')
    },
  })
  const { mutate: requestAccessKey, reset: resetAccessKey } = accessKeyMutation
  const { reset: resetRotation } = rotateMutation

  useEffect(() => {
    if (!open) {
      requestedForOpen.current = false
      resetAccessKey()
      resetRotation()
      setAccessKey(null)
      setCopied(null)
      setIsAccessKeyVisible(false)
      setIsRotationConfirmationVisible(false)
      return
    }

    if (!requestedForOpen.current) {
      requestedForOpen.current = true
      requestAccessKey()
    }
  }, [open, requestAccessKey, resetAccessKey, resetRotation])

  useEffect(() => {
    return () => {
      if (copiedTimeout.current !== null) window.clearTimeout(copiedTimeout.current)
    }
  }, [])

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && rotateMutation.isPending) return
    onOpenChange(nextOpen)
  }

  async function copy(value: string, copiedValue: Exclude<CopiedValue, null>) {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(copiedValue)
      if (copiedTimeout.current !== null) window.clearTimeout(copiedTimeout.current)
      copiedTimeout.current = window.setTimeout(() => setCopied(null), 1_500)
    } catch {
      showErrorToast(
        'Не удалось скопировать',
        'Разрешите доступ к буферу обмена и попробуйте ещё раз.',
      )
    }
  }

  return (
    <Dialog onOpenChange={handleOpenChange} open={open}>
      <DialogContent className="min-w-0 sm:max-w-md" showCloseButton={!rotateMutation.isPending}>
        <DialogHeader>
          <DialogTitle>Данные ПАК</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-5 text-sm">
          <DataField label="Код ПАК" value={pak.code} />
          <DataField label="Тип" value={pakKindLabels[pak.kind]} />
        </div>
        <CredentialField
          copied={copied === 'clientId'}
          label="Client ID"
          onCopy={() => void copy(pak.oauthClientId, 'clientId')}
          copyLabel="Копировать Client ID"
          value={pak.oauthClientId}
        />
        <div className="min-w-0 space-y-2">
          <p className="text-sm font-medium">Ключ доступа</p>
          {accessKeyMutation.isPending ? (
            <div className="flex h-9 items-center justify-center rounded-md border bg-muted">
              <Spinner />
            </div>
          ) : accessKey ? (
            <div className="flex min-w-0 items-center gap-1 rounded-md border bg-muted px-3 py-2">
              <span className="min-w-0 flex-1 truncate font-mono text-sm">
                {isAccessKeyVisible ? accessKey : '••••••••••••••••'}
              </span>
              <IconButton
                label={isAccessKeyVisible ? 'Скрыть ключ доступа' : 'Показать ключ доступа'}
                onClick={() => setIsAccessKeyVisible((visible) => !visible)}
              >
                {isAccessKeyVisible ? <EyeOffIcon /> : <EyeIcon />}
              </IconButton>
              <IconButton
                label="Копировать ключ доступа"
                onClick={() => void copy(accessKey, 'accessKey')}
              >
                {copied === 'accessKey' ? <CheckIcon /> : <CopyIcon />}
              </IconButton>
            </div>
          ) : (
            <div className="flex items-center justify-between gap-3 rounded-md border border-destructive/30 px-3 py-2 text-sm text-muted-foreground">
              <span>Не удалось загрузить ключ.</span>
              <Button
                onClick={() => accessKeyMutation.mutate()}
                size="sm"
                type="button"
                variant="outline"
              >
                Повторить
              </Button>
            </div>
          )}
        </div>
        {pak.archivedAt === null ? (
          <div className="border-t pt-4">
            {isRotationConfirmationVisible ? (
              <>
                <p className="text-sm text-muted-foreground">Старый ключ перестанет работать.</p>
                <DialogFooter className="mt-4">
                  <Button
                    disabled={rotateMutation.isPending}
                    onClick={() => setIsRotationConfirmationVisible(false)}
                    type="button"
                    variant="outline"
                  >
                    Отмена
                  </Button>
                  <Button
                    disabled={rotateMutation.isPending}
                    onClick={() => rotateMutation.mutate()}
                    type="button"
                  >
                    {rotateMutation.isPending ? <Spinner data-icon="inline-start" /> : null}
                    {rotateMutation.isPending ? 'Ротация…' : 'Ротировать'}
                  </Button>
                </DialogFooter>
              </>
            ) : (
              <Button
                className="-ml-2"
                onClick={() => setIsRotationConfirmationVisible(true)}
                type="button"
                variant="ghost"
              >
                <RotateCcwIcon data-icon="inline-start" />
                Ротировать ключ
              </Button>
            )}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

function DataField({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div className="min-w-0 space-y-1">
      <p className="text-sm font-medium">{label}</p>
      <p className="truncate text-muted-foreground">{value}</p>
    </div>
  )
}

function CredentialField({
  copied,
  copyLabel,
  label,
  onCopy,
  value,
}: Readonly<{
  copied: boolean
  copyLabel: string
  label: string
  onCopy: () => void
  value: string
}>) {
  return (
    <div className="min-w-0 space-y-2">
      <p className="text-sm font-medium">{label}</p>
      <div className="flex min-w-0 items-center gap-1 rounded-md border bg-muted px-3 py-2">
        <span className="min-w-0 flex-1 truncate font-mono text-sm">{value}</span>
        <IconButton label={copyLabel} onClick={onCopy}>
          {copied ? <CheckIcon /> : <CopyIcon />}
        </IconButton>
      </div>
    </div>
  )
}

function IconButton({
  children,
  label,
  onClick,
}: Readonly<{ children: ReactNode; label: string; onClick: () => void }>) {
  return (
    <Button aria-label={label} onClick={onClick} size="icon-sm" type="button" variant="ghost">
      {children}
    </Button>
  )
}
