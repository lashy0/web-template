import {
  ArchiveIcon,
  CircleCheckIcon,
  EllipsisVerticalIcon,
  EyeIcon,
  KeyRoundIcon,
  PencilIcon,
  PowerIcon,
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

import { EditPak } from '@/components/Pak/Paks/EditPak'
import { PakConfirmation } from '@/components/Pak/Paks/PakConfirmation'
import { RotatePakAccessKey } from '@/components/Pak/Paks/RotatePakAccessKey'
import { ViewPakAccessKey } from '@/components/Pak/Paks/ViewPakAccessKey'
import { type Pak } from '@/features/paks/paks-api'

export function PakActionsMenu({ pak }: Readonly<{ pak: Pak }>) {
  const [open, setOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [accessKeyOpen, setAccessKeyOpen] = useState(false)
  const [rotateAccessKeyOpen, setRotateAccessKeyOpen] = useState(false)
  const [confirmation, setConfirmation] = useState<
    'activate' | 'archive' | 'deactivate' | 'delete' | 'restore' | null
  >(null)
  const archived = pak.archivedAt !== null
  const closeMenu = () => setOpen(false)
  return (
    <DropdownMenu onOpenChange={setOpen} open={open}>
      <DropdownMenuTrigger
        render={<Button className="cursor-pointer" size="icon-sm" variant="ghost" />}
      >
        <EllipsisVerticalIcon />
        <span className="sr-only">Действия с ПАК {pak.code}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuGroup>
          {archived ? (
            <DropdownMenuItem onClick={() => setConfirmation('restore')}>
              <RotateCcwIcon />
              Восстановить
            </DropdownMenuItem>
          ) : (
            <>
              <DropdownMenuItem onClick={() => setAccessKeyOpen(true)}>
                <EyeIcon />
                Показать ключ
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setRotateAccessKeyOpen(true)}>
                <KeyRoundIcon />
                Ротировать ключ
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setEditOpen(true)}>
                <PencilIcon />
                Изменить
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setConfirmation(pak.status === 'active' ? 'deactivate' : 'activate')}
              >
                {pak.status === 'active' ? <PowerIcon /> : <CircleCheckIcon />}
                {pak.status === 'active' ? 'Отключить' : 'Активировать'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setConfirmation('archive')}>
                <ArchiveIcon />
                Архивировать
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="data-[variant=destructive]:hover:bg-destructive/10 data-[variant=destructive]:focus:bg-destructive/10"
          onClick={() => setConfirmation('delete')}
          variant="destructive"
        >
          <Trash2Icon />
          Удалить
        </DropdownMenuItem>
      </DropdownMenuContent>
      <EditPak onOpenChange={setEditOpen} onSuccess={closeMenu} open={editOpen} pak={pak} />
      <ViewPakAccessKey onOpenChange={setAccessKeyOpen} open={accessKeyOpen} pak={pak} />
      <RotatePakAccessKey
        onOpenChange={setRotateAccessKeyOpen}
        open={rotateAccessKeyOpen}
        pak={pak}
      />
      {confirmation ? (
        <PakConfirmation
          action={confirmation}
          onOpenChange={(next) => {
            if (!next) setConfirmation(null)
          }}
          onSuccess={closeMenu}
          open
          pak={pak}
        />
      ) : null}
    </DropdownMenu>
  )
}
