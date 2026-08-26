import { expect, test } from '@playwright/test'

test('loads the application shell and handles an unknown route', async ({ page }) => {
  const runtimeErrors: string[] = []
  page.on('pageerror', (error) => runtimeErrors.push(error.message))

  await page.goto('/')

  await expect(page).toHaveTitle('Web App')
  await expect(page.getByRole('heading', { level: 1, name: 'Нет доступа' })).toBeVisible()

  await page.goto('/missing-page')
  await expect(page.getByTestId('not-found')).toBeVisible()
  await page.getByRole('link', { name: 'На главную' }).click()
  await expect(page).toHaveURL('/')
  expect(runtimeErrors).toEqual([])
})
