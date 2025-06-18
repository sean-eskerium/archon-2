/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './test/setup.ts',
    include: ['test/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    exclude: ['node_modules', 'dist', '.git', '.cache'],
    reporters: ['basic', 'json'],
    outputFile: { 
      json: './coverage/test-results.json' 
    },
    coverage: {
      provider: 'v8',
      reporter: [
        'text', 
        'text-summary', 
        'html', 
        'json', 
        'json-summary',
        'lcov'
      ],
      reportsDirectory: './coverage',
      exclude: [
        'node_modules/',
        'test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData.ts',
        '**/*.test.{ts,tsx}',
        'src/env.d.ts',
        'coverage/**',
        'dist/**',
        'public/**',
        '**/*.stories.*',
        '**/*.story.*',
      ],
      include: [
        'src/**/*.{ts,tsx}',
      ],
      thresholds: {
        global: {
          statements: 70,
          branches: 65,
          functions: 70,
          lines: 70,
        },
        // Per file thresholds
        'src/services/**/*.ts': {
          statements: 80,
          branches: 75,
          functions: 80,
          lines: 80,
        },
        'src/components/**/*.tsx': {
          statements: 75,
          branches: 70,
          functions: 75,
          lines: 75,
        }
      }
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      'lucide-react': path.resolve(__dirname, './test/__mocks__/lucide-react.tsx'),
    },
  },
}) 