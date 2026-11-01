import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Relative base so the build works on GitHub Pages under any repo name.
// The HEIC decoder (WebAssembly) is a large chunk, but it is only loaded
// on demand when a photo can't be decoded natively.
// __BUILD__ is shown in the app footer so you can tell which version is
// running (useful for the iPhone Home Screen app, which caches pages).
const sha = (process.env.GITHUB_SHA ?? 'dev').slice(0, 7);
const date = new Date().toISOString().slice(0, 16).replace('T', ' ');

export default defineConfig({
  plugins: [react()],
  base: './',
  build: { chunkSizeWarningLimit: 4000 },
  define: { __BUILD__: JSON.stringify(`${sha} · ${date} UTC`) },
});
