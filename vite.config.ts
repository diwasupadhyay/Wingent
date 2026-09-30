/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    watch: {
      ignored: /[\\/]src-tauri[\\/]/,
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
