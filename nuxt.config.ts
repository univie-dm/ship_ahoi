// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',
  devtools: { enabled: true },
  
  // Runtime configuration
  runtimeConfig: {
    // Server-side environment variables (not exposed to client)
    apiBase: process.env.API_BASE || 'http://localhost:8000',
    redisUrl: process.env.REDIS_URL || 'redis://localhost:6379/0',
    
    // Public environment variables (exposed to client)
    public: {
      historyPersistenceEnabled: process.env.HISTORY_PERSISTENCE_ENABLED === 'true' || false,
      redisConnectionTimeout: parseInt(process.env.REDIS_CONNECTION_TIMEOUT || '5000'),
      maxCachedRuns: parseInt(process.env.MAX_CACHED_RUNS || '50')
    }
  },
  
  // Global CSS
  css: [
    '~/assets/css/sidebar-global.css'
  ],
  
  // Configure build for performance
  build: {
    analyze: false // Set to true to analyze bundle size
  },
  
  // Nitro configuration for better compatibility
  nitro: {
    experimental: {
      wasm: false
    },
    rollupConfig: {
      external: []
    },
    prerender: {
      routes: []
    },
    replace: {
      'process.env.NODE_ENV': JSON.stringify('production')
    },
    minify: false, // Disable nitro minification to prevent esbuild issues
    esbuild: {
      options: {
        target: 'es2020',
        keepNames: true,
        minifyIdentifiers: false,
        minifySyntax: false,
        minifyWhitespace: false
      }
    }
  },

  // Performance optimizations
  experimental: {
    payloadExtraction: false,
    inlineSSRStyles: false
  },

  // SSR configuration
  ssr: true,
  plugins: ['~/plugins/vTooltip.ts'],

  // Optimize rendering
  app: {
    head: {
      link: [
        // Preload critical fonts
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }
      ]
    }
  },

  // Additional config for TypeScript
  typescript: {
    strict: true,
    typeCheck: false
  },

  // Optimize bundle splitting with aggressive esbuild fixes
  vite: {
    build: {
      chunkSizeWarningLimit: 1000, // Increase warning limit for large chunks
      minify: 'terser', // Use terser instead of esbuild for production minification
      rollupOptions: {
        output: {
          manualChunks: {
            'papa-parse': ['papaparse'],
            'vue-vendor': ['vue', 'vue-router'],
            'd3-vendor': ['d3'],
            'plotly-vendor': ['plotly.js-dist']
          }
        }
      }
    },
    server: {
      allowedHosts: true
    },
    esbuild: {
      // Disable problematic esbuild optimizations
      minifyIdentifiers: false,
      minifySyntax: false,
      minifyWhitespace: false,
      keepNames: true,
      target: 'es2020'
    },
    optimizeDeps: {
      include: ['papaparse'],
      esbuildOptions: {
        target: 'es2020',
        keepNames: true,
        minifyIdentifiers: false,
        minifySyntax: false
      }
    },
    define: {
      global: 'globalThis'
    }
  }
})
