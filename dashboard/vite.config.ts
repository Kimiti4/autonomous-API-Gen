import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    port: 5173,
    proxy: {
      // Dev only; production uses the ingress.
      '/observation': { target: 'http://localhost:8080', changeOrigin: true },
      '/config': { target: 'http://localhost:8080', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8080', ws: true },
    },
  },
  build: { sourcemap: true, target: 'es2022' },
  test: { environment: 'jsdom', globals: false, setupFiles: ['./src/tests/setup.ts'] },
});
