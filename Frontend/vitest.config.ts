// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/tests/setupTests.ts'],
    include: ['src/**/*.test.{js,ts,jsx,tsx}'],
    coverage: {
      provider: 'c8',
      reporter: ['text', 'html'],
    },
  },
});
