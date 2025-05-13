import { defineConfig } from 'vite';
import { resolve } from 'path';

// No necesitamos vite-plugin-static-copy
// import { viteStaticCopy } from 'vite-plugin-static-copy'; 

export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: true, // Asegura que dist esté limpio antes de cada build
    rollupOptions: {
      input: {
        popup: resolve(__dirname, 'src/popup.html'),
        blocked: resolve(__dirname, 'public/blocked.html'),
        background: resolve(__dirname, 'src/background.ts')
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
        format: 'es'
      }
    },
    target: 'esnext',
    minify: false
  },
  // plugins: [], // Sin plugins extra por ahora
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development')
  },
  // Mueve los HTML a public también, para que se copien tal cual
  publicDir: 'public' 
}); 