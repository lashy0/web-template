import { Button } from '@web-app/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@web-app/ui/components/dialog'

import { type ProductionOrder } from '@/features/production-orders/production-order-api'

export function ViewProductionOrder({
  onOpenChange,
  open,
  order,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  open: boolean
  order: ProductionOrder
}>) {
  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Информация о производственном заказе</DialogTitle>
        </DialogHeader>
        <div className="flex max-h-[calc(100vh-14rem)] flex-col gap-5 overflow-y-auto pr-1">
          <Detail title="Название" value={order.name} />
          <Detail title="Описание" value={order.description || '—'} />
          <Detail title="Количество партий" value={String(order.batchesCount)} />
          <Detail title="Общий план" value={String(order.totalPlannedQty)} />
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

function Detail({ title, value }: Readonly<{ title: string; value: string }>) {
  return (
    <section>
      <h3 className="font-medium">{title}</h3>
      <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground [overflow-wrap:anywhere]">
        {value}
      </p>
    </section>
  )
}
