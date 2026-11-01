import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Relative base so the build works on GitHub Pages under any repo name.
// The HEIC decoder (WebAssembly) is a large chunk, but it is only loaded
// on demand when a photo can't be decoded natively.
export default defineConfig({ plugins: [react()], base: './', build: { chunkSizeWarningLimit: 4000 } });
