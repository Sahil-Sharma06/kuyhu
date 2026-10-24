import { card, expect, expectNoHorizontalScroll, openApp, test } from './fixtures'

test('pick a day and see the chart and metrics', async ({ page }) => {
  await openApp(page)
  await page.getByLabel('Delivery day (D)').fill('2026-01-15')
  await expect(card(page, 'Latest forecast used')).toContainText('14 Jan')
  await expect(card(page, 'Mean forecast')).toHaveText(/^[\d,]+ MW$/)
  await expect(card(page, 'Outturn (hindsight)')).toHaveText(/^[\d,]+ MW$/)
  const chart = page.getByRole('img', { name: /forecast, lower bound and actual/ })
  await expect(chart.locator('path.recharts-line-curve')).toHaveCount(3)
  await expectNoHorizontalScroll(page)
})

test('changing the cutoff changes the forecast used and the numbers', async ({ page }) => {
  await openApp(page)
  await page.getByLabel('Delivery day (D)').fill('2026-01-20')
  await expect(card(page, 'Latest forecast used')).toContainText('19 Jan, 09:30')
  const before = await card(page, 'Mean forecast').textContent()

  await page.getByLabel('Decision time on D-1 (London)').fill('03:00')
  await expect(card(page, 'Latest forecast used')).toContainText('19 Jan, 02:30')
  await expect(card(page, 'Mean forecast')).not.toHaveText(before!)
})

test('navigate between Decision, Accuracy and Methodology', async ({ page }) => {
  await openApp(page)
  await page.getByRole('button', { name: 'Accuracy' }).click()
  await expect(card(page, 'MAE')).toHaveText(/^[\d,]+ MW$/)
  await expect(card(page, 'MAPE')).toHaveText(/^\d+\.\d%$/)
  await expect(page.getByText('Error by forecast horizon')).toBeVisible()
  await expectNoHorizontalScroll(page)

  const mae = await card(page, 'MAE').textContent()
  await page.getByLabel('Decision time on D-1 (London)').fill('03:00')
  await expect(card(page, 'MAE')).not.toHaveText(mae!)

  await page.getByRole('button', { name: 'Methodology' }).click()
  await expect(page.getByRole('heading', { name: /Methodology/ })).toBeVisible()
  await expectNoHorizontalScroll(page)

  await page.getByRole('button', { name: 'Decision' }).click()
  await expect(page.getByText('Wind generation: latest forecast vs actual')).toBeVisible()
})

test('keyboard users can switch views and reach the controls', async ({ page }) => {
  await openApp(page)
  await page.getByRole('button', { name: 'Accuracy' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Accuracy' })).toHaveAttribute('aria-current', 'page')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Methodology' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('From')).toBeFocused()
})
