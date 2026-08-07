import { expect, test } from '@playwright/test'

test('loads the application shell and handles an unknown route', async ({ page }) => {
  const runtimeErrors: string[] = []
  page.on('pageerror', (error) => runtimeErrors.push(error.message))

  await page.goto('/')

  await expect(page).toHaveTitle('Web App')
  await expect(page.getByRole('heading', { level: 1, name: 'Web App' })).toBeVisible()

  await page.goto('/missing-page')
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible()
  await page.getByRole('link', { name: 'Back to home' }).click()
  await expect(page).toHaveURL('/')
  expect(runtimeErrors).toEqual([])
})
