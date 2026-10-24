import AxeBuilder from '@axe-core/playwright'
import { expect, openApp, test } from './fixtures'

for (const view of ['Decision', 'Accuracy', 'Methodology'] as const) {
  for (const colorScheme of ['light', 'dark'] as const) {
  test(`${view} view (${colorScheme}) has no serious or critical axe violations`, async ({ page }) => {
    // Scan settled states, not colour transitions mid-animation.
    await page.emulateMedia({ reducedMotion: 'reduce', colorScheme })
    await openApp(page)
    await page.getByRole('button', { name: view }).click()
    await page.waitForLoadState('networkidle')
    const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    const blocking = violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
    expect(blocking.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([])
  })
  }
}

test('charts expose a data table as a text alternative', async ({ page }) => {
  await openApp(page)
  await page.getByText('Show hourly table').click()
  await expect(page.getByRole('table', { name: 'Hourly forecast, lower bound and actual' })).toBeVisible()
  await page.getByRole('button', { name: 'Accuracy' }).click()
  for (const name of ['Error by forecast horizon', 'Error by hour of day', 'Error distribution', 'Daily trend']) {
    await expect(page.getByRole('table', { name, includeHidden: true })).toHaveCount(1)
  }
})
