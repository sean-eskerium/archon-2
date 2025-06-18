import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, renderHook, act } from '@testing-library/react'
import React from 'react'
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn()
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true
})

describe('ThemeContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset localStorage mock
    localStorageMock.getItem.mockReturnValue(null)
    // Clean up any existing classes
    document.documentElement.classList.remove('dark', 'light')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('ThemeProvider', () => {
    it('should provide theme value', () => {
      const TestComponent = () => {
        const { theme } = useTheme()
        return <div>Current theme: {theme}</div>
      }

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByText(/Current theme:/)).toBeInTheDocument()
    })

    it('should default to dark theme when no saved preference', () => {
      localStorageMock.getItem.mockReturnValue(null)

      const TestComponent = () => {
        const { theme } = useTheme()
        return <div>{theme}</div>
      }

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByText('dark')).toBeInTheDocument()
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark')
    })

    it('should load saved theme from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('light')

      const TestComponent = () => {
        const { theme } = useTheme()
        return <div>{theme}</div>
      }

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByText('light')).toBeInTheDocument()
      expect(localStorageMock.getItem).toHaveBeenCalledWith('theme')
    })
  })

  describe('Theme Toggling', () => {
    it('should toggle theme from dark to light', () => {
      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider
      })

      expect(result.current.theme).toBe('dark')

      act(() => {
        result.current.setTheme('light')
      })

      expect(result.current.theme).toBe('light')
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'light')
    })

    it('should toggle theme from light to dark', () => {
      localStorageMock.getItem.mockReturnValue('light')

      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider
      })

      expect(result.current.theme).toBe('light')

      act(() => {
        result.current.setTheme('dark')
      })

      expect(result.current.theme).toBe('dark')
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark')
    })

    it('should update multiple components when theme changes', () => {
      const TestComponent1 = () => {
        const { theme } = useTheme()
        return <div data-testid="comp1">{theme}</div>
      }

      const TestComponent2 = () => {
        const { theme, setTheme } = useTheme()
        return (
          <div>
            <div data-testid="comp2">{theme}</div>
            <button onClick={() => setTheme('light')}>Change</button>
          </div>
        )
      }

      render(
        <ThemeProvider>
          <TestComponent1 />
          <TestComponent2 />
        </ThemeProvider>
      )

      expect(screen.getByTestId('comp1')).toHaveTextContent('dark')
      expect(screen.getByTestId('comp2')).toHaveTextContent('dark')

      // Change theme
      screen.getByText('Change').click()

      expect(screen.getByTestId('comp1')).toHaveTextContent('light')
      expect(screen.getByTestId('comp2')).toHaveTextContent('light')
    })
  })

  describe('DOM Class Management', () => {
    it('should apply dark class to document element', () => {
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(document.documentElement.classList.contains('light')).toBe(false)
    })

    it('should apply light class when theme is light', () => {
      localStorageMock.getItem.mockReturnValue('light')

      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(document.documentElement.classList.contains('light')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })

    it('should remove previous theme class when switching', () => {
      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider
      })

      // Initially dark
      expect(document.documentElement.classList.contains('dark')).toBe(true)

      act(() => {
        result.current.setTheme('light')
      })

      expect(document.documentElement.classList.contains('light')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(false)

      act(() => {
        result.current.setTheme('dark')
      })

      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(document.documentElement.classList.contains('light')).toBe(false)
    })
  })

  describe('LocalStorage Persistence', () => {
    it('should persist theme preference to localStorage', () => {
      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider
      })

      act(() => {
        result.current.setTheme('light')
      })

      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'light')

      act(() => {
        result.current.setTheme('dark')
      })

      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark')
    })

    it('should save default theme on initial load', () => {
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      // Should save 'dark' as default
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark')
    })
  })

  describe('Error Handling', () => {
    it('should throw error when useTheme is used outside ThemeProvider', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const TestComponent = () => {
        const { theme } = useTheme()
        return <div>{theme}</div>
      }

      expect(() => {
        render(<TestComponent />)
      }).toThrow('useTheme must be used within a ThemeProvider')

      consoleSpy.mockRestore()
    })
  })

  describe('Edge Cases', () => {
    it('should handle invalid localStorage values gracefully', () => {
      localStorageMock.getItem.mockReturnValue('invalid-theme')

      const TestComponent = () => {
        const { theme } = useTheme()
        return <div>{theme}</div>
      }

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      // Should fall back to dark theme
      expect(screen.getByText('dark')).toBeInTheDocument()
    })

    it('should handle localStorage errors gracefully', () => {
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error('localStorage is full')
      })

      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider
      })

      // Should not throw when setting theme
      expect(() => {
        act(() => {
          result.current.setTheme('light')
        })
      }).not.toThrow()

      // Theme should still update in state
      expect(result.current.theme).toBe('light')
    })

    it('should handle rapid theme changes', () => {
      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider
      })

      act(() => {
        result.current.setTheme('light')
        result.current.setTheme('dark')
        result.current.setTheme('light')
        result.current.setTheme('dark')
      })

      expect(result.current.theme).toBe('dark')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(document.documentElement.classList.contains('light')).toBe(false)
    })
  })

  describe('Children Rendering', () => {
    it('should render children components', () => {
      render(
        <ThemeProvider>
          <div data-testid="child1">Child 1</div>
          <div data-testid="child2">Child 2</div>
        </ThemeProvider>
      )

      expect(screen.getByTestId('child1')).toBeInTheDocument()
      expect(screen.getByTestId('child2')).toBeInTheDocument()
    })

    it('should not re-render children unnecessarily', () => {
      let renderCount = 0

      const TestComponent = () => {
        renderCount++
        const { theme } = useTheme()
        return <div>Theme: {theme}, Renders: {renderCount}</div>
      }

      const { rerender } = render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      expect(renderCount).toBe(1)

      // Re-render with same props shouldn't trigger child re-render
      rerender(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      // Only one additional render for the rerender
      expect(renderCount).toBe(2)
    })
  })
})