import { Button } from '@web-app/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@web-app/ui/components/dialog'

import { type DefectType } from '@/features/defects/defects-api'

export function ViewDefectType({
  onOpenChange,
  open,
  type,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  open: boolean
  type: DefectType
}>) {
  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{type.name}</DialogTitle>
          <DialogDescription>
            Тип «{type.code}» в группе {type.group.code} ({type.group.name}).
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[calc(100vh-14rem)] space-y-5 overflow-y-auto pr-1">
          <DetailSection title="Описание" value={type.description} />
          {type.possibleCause ? (
            <DetailSection title="Возможная причина" value={type.possibleCause} />
          ) : null}
          {type.engineerAction ? (
            <DetailSection title="Действие инженера" value={type.engineerAction} />
          ) : null}
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
