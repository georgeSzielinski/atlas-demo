import { defineConfig } from 'vitest/config'

// Vitest-only config. Kept separate from vite.config.js on purpose: `vite build`
// never loads this file, so the production build has no dependency on vitest.
// The selectors under test are pure functions, so the default `node`
// environment is enough — no jsdom/happy-dom, no DOM globals.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
    globals: false,
  },
})
