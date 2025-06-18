import { vi } from 'vitest'

export const mockLocalStorage = () => {
  const storage: Record<string, string> = {}
  
  return {
    getItem: vi.fn((key: string) => storage[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      storage[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete storage[key]
    }),
    clear: vi.fn(() => {
      Object.keys(storage).forEach(key => delete storage[key])
    })
  }
}

export const mockConsole = () => {
  const originalConsole = { ...console }
  
  return {
    mockError: () => {
      console.error = vi.fn()
    },
    mockWarn: () => {
      console.warn = vi.fn()
    },
    mockLog: () => {
      console.log = vi.fn()
    },
    restore: () => {
      console.error = originalConsole.error
      console.warn = originalConsole.warn
      console.log = originalConsole.log
    }
  }
}

export const waitForAsync = (ms = 0) => 
  new Promise(resolve => setTimeout(resolve, ms))

export const mockIntersectionObserver = () => {
  global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn()
  }))
}

export const mockMatchMedia = (matches = false) => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}