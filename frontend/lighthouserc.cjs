/** Lighthouse CI: audits the production preview build (backend must be running on :8000). */
module.exports = {
  ci: {
    collect: {
      url: ['http://localhost:4173/'],
      startServerCommand: 'npx vite preview --port 4173 --strictPort',
      startServerReadyPattern: 'Local',
      numberOfRuns: 3,
      settings: { preset: 'desktop', chromeFlags: '--headless=new --no-sandbox' },
    },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.8 }],
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['warn', { minScore: 0.9 }],
      },
    },
    upload: { target: 'filesystem', outputDir: '.lighthouseci' },
  },
}
