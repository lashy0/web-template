import {
  ArchiveIcon,
  CircleCheckIcon,
  KeyRoundIcon,
  EllipsisVerticalIcon,
  PencilIcon,
  RotateCcwIcon,
  Trash2Icon,
  UserRoundXIcon,
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

import { ArchiveStatusUser } from '@/components/User/Users/ArchiveStatusUser'
import { ChangeUserPassword } from '@/components/User/Users/ChangeUserPassword'
import { DeleteUser } from '@/components/User/Users/DeleteUser'
import { EditUser } from '@/components/User/Users/EditUser'
import { StatusUser } from '@/components/User/Users/StatusUser'
import { type User } from '@/features/users/users-api'
import useAuth from '@/hooks/useAuth'

export function UserActionsMenu({ user }: Readonly<{ user: User }>) {
  const [open, setOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [changePasswordOpen, setChangePasswordOpen] = useState(false)
  const [statusOpen, setStatusOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const { user: currentUser } = useAuth()

  if (!currentUser || user.id === currentUser.id) {
    return null
  }

  const isArchived = user.archivedAt !== null

  return (
    <DropdownMenu onOpenChange={setOpen} open={open}>
      <DropdownMenuTrigger
        render={<Button className="cursor-pointer" size="icon-sm" variant="ghost" />}
      >
        <EllipsisVerticalIcon />
        <span className="sr-only">Действия с пользователем {user.name}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuGroup>
          {isArchived ? (
            <DropdownMenuItem onClick={() => setArchiveOpen(true)}>
              <RotateCcwIcon />
              Восстановить
            </DropdownMenuItem>
          ) : (
            <>
              <DropdownMenuItem onClick={() => setEditOpen(true)}>
                <PencilIcon />
                Изменить
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setChangePasswordOpen(true)}>
                <KeyRoundIcon />
                Сменить пароль
              </DropdownMenuItem>

              {user.authState === 'active' ? (
                <DropdownMenuItem onClick={() => setStatusOpen(true)}>
                  <UserRoundXIcon />
                  Деактивировать
                </DropdownMenuItem>
              ) : null}

              {user.authState === 'inactive' ? (
                <DropdownMenuItem onClick={() => setStatusOpen(true)}>
                  <CircleCheckIcon />
                  Активировать
                </DropdownMenuItem>
              ) : null}

              <DropdownMenuItem onClick={() => setArchiveOpen(true)}>
                <ArchiveIcon />
                Архивировать
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="data-[variant=destructive]:hover:bg-destructive/10 data-[variant=destructive]:focus:bg-destructive/10"
          variant="destructive"
          onClick={() => setDeleteOpen(true)}
        >
          <Trash2Icon />
          Удалить
        </DropdownMenuItem>
      </DropdownMenuContent>
      <EditUser
        onOpenChange={setEditOpen}
        onSuccess={() => setOpen(false)}
        open={editOpen}
        user={user}
      />
      <ChangeUserPassword
        onOpenChange={setChangePasswordOpen}
        onSuccess={() => setOpen(false)}
        open={changePasswordOpen}
        user={user}
      />
      <StatusUser
        onOpenChange={setStatusOpen}
        onSuccess={() => setOpen(false)}
        open={statusOpen}
        user={user}
      />
      <ArchiveStatusUser
        onOpenChange={setArchiveOpen}
        onSuccess={() => setOpen(false)}
        open={archiveOpen}
        user={user}
      />
      <DeleteUser
        onOpenChange={setDeleteOpen}
        onSuccess={() => setOpen(false)}
        open={deleteOpen}
        user={user}
      />
    </DropdownMenu>
  )
}
