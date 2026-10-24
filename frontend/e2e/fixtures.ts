import { test as base, expect, type Page } from '@playwright/test'

/** Fails any test whose page logs a console error or throws an uncaught exception. */
export const test = base.extend<{ consoleErrors: string[] }>({
  consoleErrors: [
    async ({ page }, use) => {
      const errors: string[] = []
      page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
      page.on('pageerror', (e) => errors.push(e.message))
      await use(errors)
      expect(errors, 'console errors').toEqual([])
    },
    { auto: true },
  ],
})

export { expect }

export const card = (page: Page, label: string) => page.getByRole('region', { name: label }).locator('p').nth(1)

export async function openApp(page: Page) {
  await page.goto('/')
  await expect(card(page, 'Latest forecast used')).not.toBeEmpty()
}

export async function expectNoHorizontalScroll(page: Page) {
  const [scroll, client] = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth])
  expect(scroll).toBeLessThanOrEqual(client)
}
