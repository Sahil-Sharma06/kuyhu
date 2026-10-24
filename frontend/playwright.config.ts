import { defineConfig, devices } from '@playwright/test'

/**
 * E2E suite. By default it starts the backend (uvicorn) and a production preview of the
 * frontend. Set E2E_BASE_URL to run the same suite as a smoke test against a deployed app
 * (e.g. https://<project>.vercel.app); no local servers are started then.
 */
const deployed = process.env.E2E_BASE_URL
const python = process.env.PYTHON ?? (process.platform === 'win32' ? '.venv/Scripts/python' : '.venv/bin/python')

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: deployed ?? 'http://localhost:4173',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'mobile-375', use: { ...devices['Desktop Chrome'], viewport: { width: 375, height: 812 } } },
    { name: 'tablet-768', use: { ...devices['Desktop Chrome'], viewport: { width: 768, height: 1024 } } },
    { name: 'desktop-1440', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
  ],
  webServer: deployed
    ? undefined
    : [
        {
          command: `${python} -m uvicorn app.main:app --port 8000`,
          cwd: '../backend',
          url: 'http://localhost:8000/api/health',
          reuseExistingServer: !process.env.CI,
        },
        {
          command: 'npm run build && npx vite preview --port 4173 --strictPort',
          url: 'http://localhost:4173',
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      ],
})
