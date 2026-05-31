import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./setup.js'],
    include: ['**/*.spec.jsx'],
    globals: true,
  },
});
