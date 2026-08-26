import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { Button } from '#components/button'
import { Input } from '#components/input'
import { cn } from '#lib/utils'

const inputGroupVariants = cva(
  'group/input-group relative flex w-full min-w-0 items-center rounded-md border shadow-xs transition-[color,box-shadow] outline-none has-[[data-slot=input-group-control]:focus-visible]:border-ring has-[[data-slot=input-group-control]:focus-visible]:ring-[3px] has-[[data-slot=input-group-control]:focus-visible]:ring-ring/50 has-[[data-slot][aria-invalid=true]]:border-destructive has-[[data-slot][aria-invalid=true]]:ring-destructive/20',
  {
    variants: {
      size: {
        default: 'h-9',
        lg: 'h-13',
      },
      variant: {
        default: 'border-input',
        auth: 'border-primary/25',
      },
    },
    defaultVariants: {
      size: 'default',
      variant: 'default',
    },
  },
)

function InputGroup({
  className,
  size,
  variant,
  ...props
}: React.ComponentProps<'div'> & VariantProps<typeof inputGroupVariants>) {
  return (
    <div
      data-slot="input-group"
      className={cn(inputGroupVariants({ size, variant }), className)}
      {...props}
    />
  )
}

const inputGroupAddonVariants = cva(
  'flex h-auto cursor-text items-center justify-center gap-2 py-1.5 text-sm font-medium text-muted-foreground select-none',
  {
    variants: {
      align: {
        'inline-end': 'order-last pr-1.5',
      },
    },
  },
)

function InputGroupAddon({
  align = 'inline-end',
  className,
  ...props
}: React.ComponentProps<'div'> & VariantProps<typeof inputGroupAddonVariants>) {
  return (
    <div
      data-slot="input-group-addon"
      data-align={align}
      className={cn(inputGroupAddonVariants({ align }), className)}
      {...props}
    />
  )
}

function InputGroupButton({
  className,
  type = 'button',
  ...props
}: React.ComponentProps<typeof Button>) {
  return (
    <Button
      className={cn('h-7 px-2 text-xs shadow-none', className)}
      type={type}
      variant="ghost"
      {...props}
    />
  )
}

function InputGroupInput({
  className,
  size,
  variant,
  ...props
}: React.ComponentProps<typeof Input>) {
  return (
    <Input
      data-slot="input-group-control"
      size={size}
      variant={variant}
      className={cn(
        'flex-1 rounded-none border-0 bg-transparent shadow-none focus-visible:ring-0 aria-invalid:border-0 aria-invalid:ring-0',
        className,
      )}
      {...props}
    />
  )
}

export { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput }
