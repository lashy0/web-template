import {
  ArchiveIcon,
  EllipsisVerticalIcon,
  EyeIcon,
  PencilIcon,
  RotateCcwIcon,
  Trash2Icon,
} from 'lucide-react'
import { useState } from 'react'

import { Button } from '@web-app/ui/components/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@web-app/ui/components/dropdown-menu'

import { type ProductionOrder } from '@/features/production-orders/production-order-api'

import { ArchiveStatusProductionOrder } from './ArchiveStatusProductionOrder'
import { DeleteProductionOrder } from './DeleteProductionOrder'
import { EditProductionOrder } from './EditProductionOrder'
import { ViewProductionOrder } from './ViewProductionOrder'

export function ProductionOrderActionsMenu({ order }: Readonly<{ order: ProductionOrder }>) {
  const [open, setOpen] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const closeMenu = () => setOpen(false)

  return (
    <DropdownMenu onOpenChange={setOpen} open={open}>
      <DropdownMenuTrigger
        render={<Button className="cursor-pointer" size="icon-sm" variant="ghost" />}
      >
        <EllipsisVerticalIcon />
        <span className="sr-only">Действия с заказом {order.name}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuGroup>
          <DropdownMenuItem onClick={() => setDetailsOpen(true)}>
            <EyeIcon />
            Подробнее
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setEditOpen(true)}>
            <PencilIcon />
            Редактировать
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setArchiveOpen(true)}>
            {order.archivedAt ? <RotateCcwIcon /> : <ArchiveIcon />}
            {order.archivedAt ? 'Восстановить' : 'Архивировать'}
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => setDeleteOpen(true)} variant="destructive">
          <Trash2Icon />
          Удалить
        </DropdownMenuItem>
      </DropdownMenuContent>
      <ViewProductionOrder onOpenChange={setDetailsOpen} open={detailsOpen} order={order} />
      <EditProductionOrder
        onOpenChange={setEditOpen}
        onSuccess={closeMenu}
        open={editOpen}
        order={order}
      />
      <ArchiveStatusProductionOrder
        onOpenChange={setArchiveOpen}
        onSuccess={closeMenu}
        open={archiveOpen}
        order={order}
      />
      <DeleteProductionOrder
        onOpenChange={setDeleteOpen}
        onSuccess={closeMenu}
        open={deleteOpen}
        order={order}
      />
    </DropdownMenu>
  )
}
