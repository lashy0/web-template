import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AddBatch } from '@/components/Batches/AddBatch'
import { listKgPrefixes } from '@/features/kg/kg-prefixes-api'
import { listKgVersions } from '@/features/kg/kg-versions-api'
import { listProductionOrders } from '@/features/production-orders/production-order-api'

vi.mock('@/features/kg/kg-prefixes-api', () => ({ listKgPrefixes: vi.fn<typeof listKgPrefixes>() }))
vi.mock('@/features/kg/kg-versions-api', () => ({ listKgVersions: vi.fn<typeof listKgVersions>() }))
vi.mock('@/features/production-orders/production-order-api', () => ({
  listProductionOrders: vi.fn<typeof listProductionOrders>(),
  productionOrderQueryKeys: { list: () => ['orders'] },
}))

const empty = { items: [], page: 1, pageSize: 100, total: 0 }
afterEach(cleanup)
beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(listKgPrefixes).mockResolvedValue(empty)
  vi.mocked(listKgVersions).mockResolvedValue(empty)
  vi.mocked(listProductionOrders).mockResolvedValue(empty)
})

async function openForm() {
  const user = userEvent.setup()
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <AddBatch />
    </QueryClientProvider>,
  )
  await user.click(screen.getByRole('button', { name: 'Добавить' }))
  return user
}

async function fillFirstStep(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByRole('textbox', { name: 'Название' }), 'Партия 123')
  await user.type(screen.getByRole('textbox', { name: 'План' }), '100')
  await user.type(screen.getByRole('textbox', { name: 'Дневной план' }), '10')
  await user.click(screen.getByRole('button', { name: 'Далее' }))
}

describe('Create batch form', () => {
  it('validates the first step and preserves values when navigating back', async () => {
    const user = await openForm()
    await user.click(screen.getByRole('button', { name: 'Далее' }))
    expect(await screen.findByText('Укажите название.')).toBeVisible()
    expect(screen.getByRole('textbox', { name: 'Название' })).toHaveFocus()
    await user.type(screen.getByRole('textbox', { name: 'Название' }), 'П')
    await waitFor(() =>
      expect(screen.queryByText('Укажите название.')).not.toBeInTheDocument(),
    )
    await user.clear(screen.getByRole('textbox', { name: 'Название' }))
    await fillFirstStep(user)
    expect(await screen.findByRole('combobox', { name: 'Тип активации' })).toHaveTextContent('ABP')
    expect(screen.getByRole('combobox', { name: 'Версия LoRaWAN' })).toHaveTextContent('1.1')
    await user.click(screen.getByRole('button', { name: 'Назад' }))
    expect(screen.getByRole('textbox', { name: 'Название' })).toHaveValue('Партия 123')
    expect(screen.getByRole('textbox', { name: 'План' })).toHaveValue('100')
    expect(screen.getByRole('textbox', { name: 'Дневной план' })).toHaveValue('10')
  })

  it('shows an error and retries loading a required list', async () => {
    vi.mocked(listKgPrefixes).mockRejectedValueOnce(new Error('offline')).mockResolvedValue(empty)
    const user = await openForm()
    await fillFirstStep(user)
    expect(await screen.findByText('Не удалось загрузить список.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Повторить' }))
    await waitFor(() =>
      expect(screen.queryByText('Не удалось загрузить список.')).not.toBeInTheDocument(),
    )
    expect(listKgPrefixes).toHaveBeenCalledTimes(2)
    expect(screen.getAllByText('Нет доступных вариантов.')).toHaveLength(2)
  })

  it('does not validate an empty select when it is opened, but validates it on submission', async () => {
    vi.mocked(listKgVersions).mockResolvedValue({
      ...empty,
      items: [
        {
          id: '123e4567-e89b-42d3-a456-426614174000',
          code: 'v1',
          batchCount: 0,
          description: null,
          name: '',
          archivedAt: null,
          createdAt: '',
          updatedAt: '',
        },
      ],
    })
    const user = await openForm()
    await fillFirstStep(user)
    const version = await screen.findByRole('combobox', { name: 'Версия КГ' })
    await user.click(version)
    expect(screen.queryByText('Выберите версию КГ.')).not.toBeInTheDocument()
    await user.keyboard('{Escape}')
    await user.click(screen.getByRole('button', { name: 'Создать партию' }))
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'DevEUI-префикс' })).toHaveFocus(),
    )
  })

})
