import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, renderHook, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { ToastProvider, useToast } from '@/contexts/ToastContext'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>
}))

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  CheckCircle: () => <div data-testid="check-icon">✓</div>,
  XCircle: () => <div data-testid="error-icon">✗</div>,
  Info: () => <div data-testid="info-icon">i</div>,
  AlertCircle: () => <div data-testid="warning-icon">!</div>,
  X: ({ onClick }: { onClick?: () => void }) => <button data-testid="close-button" onClick={onClick}>×</button>
}))

describe('ToastContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('ToastProvider', () => {
    it('should provide toast context', () => {
      const TestComponent = () => {
        const { showToast } = useToast()
        return (
          <button onClick={() => showToast('Test message')}>
            Show Toast
          </button>
        )
      }

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      )

      expect(screen.getByText('Show Toast')).toBeInTheDocument()
    })

    it('should show toast messages', () => {
      const TestComponent = () => {
        const { showToast } = useToast()
        return (
          <button onClick={() => showToast('Hello world!')}>
            Show Toast
          </button>
        )
      }

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      )

      // Initially no toast
      expect(screen.queryByText('Hello world!')).not.toBeInTheDocument()

      // Show toast
      screen.getByText('Show Toast').click()

      // Toast should appear
      expect(screen.getByText('Hello world!')).toBeInTheDocument()
    })
  })

  describe('Toast Types', () => {
    it('should support different toast types', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('Success message', 'success')
        result.current.showToast('Error message', 'error')
        result.current.showToast('Warning message', 'warning')
        result.current.showToast('Info message', 'info')
      })

      expect(screen.getByText('Success message')).toBeInTheDocument()
      expect(screen.getByText('Error message')).toBeInTheDocument()
      expect(screen.getByText('Warning message')).toBeInTheDocument()
      expect(screen.getByText('Info message')).toBeInTheDocument()

      // Check icons
      expect(screen.getByTestId('check-icon')).toBeInTheDocument()
      expect(screen.getByTestId('error-icon')).toBeInTheDocument()
      expect(screen.getByTestId('warning-icon')).toBeInTheDocument()
      expect(screen.getAllByTestId('info-icon')).toHaveLength(1)
    })

    it('should default to info type', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('Default type message')
      })

      expect(screen.getByTestId('info-icon')).toBeInTheDocument()
    })

    it('should apply correct styles for each type', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('Success', 'success')
      })

      const successToast = screen.getByText('Success').closest('div')
      expect(successToast).toHaveClass('from-green-50/95', 'to-emerald-50/95')

      act(() => {
        result.current.showToast('Error', 'error')
      })

      const errorToast = screen.getByText('Error').closest('div')
      expect(errorToast).toHaveClass('from-red-50/95', 'to-pink-50/95')
    })
  })

  describe('Auto Dismissal', () => {
    it('should auto-dismiss toasts after default duration', async () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('Auto dismiss')
      })

      expect(screen.getByText('Auto dismiss')).toBeInTheDocument()

      // Fast forward time
      act(() => {
        vi.advanceTimersByTime(4000)
      })

      await waitFor(() => {
        expect(screen.queryByText('Auto dismiss')).not.toBeInTheDocument()
      })
    })

    it('should respect custom duration', async () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('Custom duration', 'info', 2000)
      })

      expect(screen.getByText('Custom duration')).toBeInTheDocument()

      // Should still be there after 1 second
      act(() => {
        vi.advanceTimersByTime(1000)
      })
      expect(screen.getByText('Custom duration')).toBeInTheDocument()

      // Should be gone after 2 seconds
      act(() => {
        vi.advanceTimersByTime(1000)
      })

      await waitFor(() => {
        expect(screen.queryByText('Custom duration')).not.toBeInTheDocument()
      })
    })

    it('should not auto-dismiss with duration 0', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('Permanent toast', 'info', 0)
      })

      expect(screen.getByText('Permanent toast')).toBeInTheDocument()

      // Fast forward a long time
      act(() => {
        vi.advanceTimersByTime(10000)
      })

      // Should still be there
      expect(screen.getByText('Permanent toast')).toBeInTheDocument()
    })
  })

  describe('Manual Dismissal', () => {
    it('should allow manual dismissal', async () => {
      const user = userEvent.setup({ delay: null })
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('Dismissible toast')
      })

      expect(screen.getByText('Dismissible toast')).toBeInTheDocument()

      // Click close button
      await user.click(screen.getByTestId('close-button'))

      expect(screen.queryByText('Dismissible toast')).not.toBeInTheDocument()
    })

    it('should dismiss only the clicked toast', async () => {
      const user = userEvent.setup({ delay: null })
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('Toast 1')
        result.current.showToast('Toast 2')
        result.current.showToast('Toast 3')
      })

      expect(screen.getByText('Toast 1')).toBeInTheDocument()
      expect(screen.getByText('Toast 2')).toBeInTheDocument()
      expect(screen.getByText('Toast 3')).toBeInTheDocument()

      // Close the second toast
      const closeButtons = screen.getAllByTestId('close-button')
      await user.click(closeButtons[1])

      expect(screen.getByText('Toast 1')).toBeInTheDocument()
      expect(screen.queryByText('Toast 2')).not.toBeInTheDocument()
      expect(screen.getByText('Toast 3')).toBeInTheDocument()
    })
  })

  describe('Multiple Toasts', () => {
    it('should handle multiple toasts', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('First toast')
        result.current.showToast('Second toast')
        result.current.showToast('Third toast')
      })

      expect(screen.getByText('First toast')).toBeInTheDocument()
      expect(screen.getByText('Second toast')).toBeInTheDocument()
      expect(screen.getByText('Third toast')).toBeInTheDocument()
    })

    it('should stack toasts vertically', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('Toast 1')
        result.current.showToast('Toast 2')
      })

      const toastContainer = screen.getByText('Toast 1').closest('.space-y-2')
      expect(toastContainer).toBeInTheDocument()
    })

    it('should handle rapid toast creation', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        for (let i = 0; i < 10; i++) {
          result.current.showToast(`Rapid toast ${i}`)
        }
      })

      for (let i = 0; i < 10; i++) {
        expect(screen.getByText(`Rapid toast ${i}`)).toBeInTheDocument()
      }
    })
  })

  describe('Toast Positioning', () => {
    it('should position toasts in top-right corner', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('Positioned toast')
      })

      const toastContainer = screen.getByText('Positioned toast').parentElement?.parentElement
      expect(toastContainer).toHaveClass('fixed', 'top-4', 'right-4', 'z-50')
    })
  })

  describe('Error Handling', () => {
    it('should throw error when useToast used outside provider', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const TestComponent = () => {
        const { showToast } = useToast()
        return <button onClick={() => showToast('Test')}>Show</button>
      }

      expect(() => {
        render(<TestComponent />)
      }).toThrow('useToast must be used within a ToastProvider')

      consoleSpy.mockRestore()
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty message', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      act(() => {
        result.current.showToast('')
      })

      // Toast should still render with just the icon
      expect(screen.getByTestId('info-icon')).toBeInTheDocument()
    })

    it('should handle very long messages', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      const longMessage = 'This is a very long message '.repeat(10)

      act(() => {
        result.current.showToast(longMessage)
      })

      expect(screen.getByText(longMessage)).toBeInTheDocument()
      const toast = screen.getByText(longMessage).closest('div')
      expect(toast).toHaveClass('max-w-[500px]')
    })

    it('should generate unique IDs for toasts', () => {
      const { result } = renderHook(() => useToast(), {
        wrapper: ToastProvider
      })

      // Create toasts at slightly different times
      act(() => {
        result.current.showToast('Toast 1')
      })

      // Small time advance to ensure different timestamp
      act(() => {
        vi.advanceTimersByTime(1)
      })

      act(() => {
        result.current.showToast('Toast 1') // Same message
      })

      // Both should exist
      const toasts = screen.getAllByText('Toast 1')
      expect(toasts).toHaveLength(2)
    })
  })

  describe('Children Rendering', () => {
    it('should render children components', () => {
      render(
        <ToastProvider>
          <div data-testid="child">Child Component</div>
        </ToastProvider>
      )

      expect(screen.getByTestId('child')).toBeInTheDocument()
    })
  })
})