import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
const root = new URL('.', import.meta.url).pathname;
export default defineConfig({
  root,
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:3000' } },
  build: { outDir: 'dist', emptyOutDir: true },
});
