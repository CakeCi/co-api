import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => ({
  base: '/static/',
  plugins: [
    vue()
  ],
  
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: mode === 'development',
    
    // Optimize chunk size
    chunkSizeWarningLimit: 500,
    
    rollupOptions: {
      output: {
        // Code splitting strategy
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia'],
          'echarts': ['echarts'],
          'utils': ['axios']
        },
        
        // Optimize asset file names
        entryFileNames: 'js/[name]-[hash].js',
        chunkFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name || ''
          if (info.endsWith('.css')) {
            return 'css/[name]-[hash][extname]'
          }
          if (info.endsWith('.png') || info.endsWith('.jpg') || info.endsWith('.jpeg') || info.endsWith('.gif') || info.endsWith('.svg')) {
            return 'img/[name]-[hash][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        }
      }
    },
    
    // Minification options (using default esbuild)
    minify: 'esbuild'
  },
  
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true
      },
      '/v1': {
        target: 'http://localhost:3000',
        changeOrigin: true
      }
    }
  },
  
  // Optimize dependencies
  optimizeDeps: {
    include: ['vue', 'vue-router', 'pinia', 'echarts', 'axios'],
    exclude: []
  },
  
  // CSS optimization
  css: {
    devSourcemap: true,
    preprocessorOptions: {
      scss: {
        additionalData: ''
      }
    }
  }
}))
