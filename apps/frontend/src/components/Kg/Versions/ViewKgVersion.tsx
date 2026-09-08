import { Button } from '@web-app/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@web-app/ui/components/dialog'

import { type KgVersion } from '@/features/kg/kg-versions-api'

export function ViewKgVersion({
  onOpenChange,
  open,
  version,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  open: boolean
  version: KgVersion
}>) {
  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Информация о версии КГ</DialogTitle>
        </DialogHeader>
        <div className="max-h-[calc(100vh-14rem)] space-y-5 overflow-y-auto pr-1">
          <DetailSection title="Название" value={version.name} />
          <DetailSection title="Код" value={version.code} />
          <DetailSection title="Описание" value={version.description || '—'} />
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} type="button">
            Готово
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DetailSection({ title, value }: Readonly<{ title: string; value: string }>) {
  return (
    <section>
      <h3 className="font-medium">{title}</h3>
      <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground [overflow-wrap:anywhere]">
        {value}
      </p>
    </section>
  )
}
