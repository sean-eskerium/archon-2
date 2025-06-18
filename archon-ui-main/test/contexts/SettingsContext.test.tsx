// Clear the global mocks for this test BEFORE imports
vi.unmock('@/contexts/SettingsContext')
vi.unmock('@/contexts/ThemeContext')
vi.unmock('@/contexts/ToastContext')

import { describe, it, expect, vi, beforeEach, afterEach, MockedFunction } from 'vitest'
import { render, screen, renderHook, act, waitFor } from '@testing-library/react'
import React from 'react'
import { credentialsService } from '@/services/credentialsService'
import { SettingsProvider, useSettings } from '@/contexts/SettingsContext'

vi.mock('@/services/credentialsService', () => ({
  credentialsService: {
    getCredential: vi.fn(),
    createCredential: vi.fn(),
    updateCredential: vi.fn(),
    deleteCredential: vi.fn()
  }
}))

const mockGetCredential = credentialsService.getCredential as MockedFunction<typeof credentialsService.getCredential>
const mockCreateCredential = credentialsService.createCredential as MockedFunction<typeof credentialsService.createCredential>

describe('SettingsContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default mock responses - settings not found defaults to enabled
    mockGetCredential.mockRejectedValue(new Error('Not found'))
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Core Functionality', () => {
    it('should provide settings to child components', async () => {
      const TestComponent = () => {
        const settings = useSettings()
        if (!settings) return <div>No settings</div>
        
        return (
          <div>
            <div data-testid="projects-status">
              Projects: {settings.projectsEnabled ? 'enabled' : 'disabled'}
            </div>
            <div data-testid="loading-status">
              Loading: {settings.loading ? 'yes' : 'no'}
            </div>
          </div>
        )
      }

      render(
        <SettingsProvider>
          <TestComponent />
        </SettingsProvider>
      )

      // Wait for settings to load
      await waitFor(() => {
        expect(screen.getByTestId('loading-status')).toHaveTextContent('Loading: no')
      })

      expect(screen.getByTestId('projects-status')).toHaveTextContent('Projects: enabled')
    })

    it('should load user preferences on mount', async () => {
      // User has disabled projects
      mockGetCredential.mockResolvedValueOnce({ value: 'false' })

      const { result } = renderHook(() => useSettings(), {
        wrapper: ({ children }) => <SettingsProvider>{children}</SettingsProvider>
      })

      // Initially loading
      expect(result.current?.loading).toBe(true)

      await waitFor(() => {
        expect(result.current?.loading).toBe(false)
      })

      // Should load user preference
      expect(result.current?.projectsEnabled).toBe(false)
      expect(mockGetCredential).toHaveBeenCalledWith('PROJECTS_ENABLED')
    })

    it('should default to enabled when preference not set', async () => {
      mockGetCredential.mockRejectedValueOnce(new Error('Not found'))

      const { result } = renderHook(() => useSettings(), {
        wrapper: ({ children }) => <SettingsProvider>{children}</SettingsProvider>
      })

      await waitFor(() => {
        expect(result.current?.loading).toBe(false)
      })

      // Should default to enabled for better user experience
      expect(result.current?.projectsEnabled).toBe(true)
    })
  })

  describe('User Interactions', () => {
    it('should allow user to toggle project feature', async () => {
      mockCreateCredential.mockResolvedValueOnce(undefined)

      const ToggleComponent = () => {
        const settings = useSettings()
        if (!settings) return null

        return (
          <div>
            <div data-testid="status">
              {settings.projectsEnabled ? 'Projects ON' : 'Projects OFF'}
            </div>
            <button 
              onClick={() => settings.setProjectsEnabled(!settings.projectsEnabled)}
              data-testid="toggle"
            >
              Toggle Projects
            </button>
          </div>
        )
      }

      render(
        <SettingsProvider>
          <ToggleComponent />
        </SettingsProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('status')).toHaveTextContent('Projects ON')
      })

      // User toggles the feature
      act(() => {
        screen.getByTestId('toggle').click()
      })

      // UI updates immediately for good UX
      expect(screen.getByTestId('status')).toHaveTextContent('Projects OFF')

      // Verify it persists the preference
      await waitFor(() => {
        expect(mockCreateCredential).toHaveBeenCalledWith({
          key: 'PROJECTS_ENABLED',
          value: 'false',
          is_encrypted: false,
          category: 'features',
          description: 'Enable or disable Projects and Tasks functionality'
        })
      })
    })

    it('should handle save failures gracefully', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockCreateCredential.mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useSettings(), {
        wrapper: ({ children }) => <SettingsProvider>{children}</SettingsProvider>
      })

      await waitFor(() => {
        expect(result.current?.loading).toBe(false)
      })

      const initialState = result.current?.projectsEnabled

      // Try to update
      await act(async () => {
        try {
          await result.current?.setProjectsEnabled(!initialState)
        } catch (error) {
          // Expected to throw
        }
      })

      // Should revert to original state on failure
      expect(result.current?.projectsEnabled).toBe(initialState)
      expect(consoleError).toHaveBeenCalled()
      
      consoleError.mockRestore()
    })

    it('should provide immediate feedback (optimistic updates)', async () => {
      let resolveUpdate: () => void
      const updatePromise = new Promise<void>(resolve => {
        resolveUpdate = resolve
      })
      
      mockCreateCredential.mockImplementationOnce(() => updatePromise)

      const { result } = renderHook(() => useSettings(), {
        wrapper: ({ children }) => <SettingsProvider>{children}</SettingsProvider>
      })

      await waitFor(() => {
        expect(result.current?.loading).toBe(false)
      })

      const initialState = result.current?.projectsEnabled

      // Start update
      act(() => {
        result.current?.setProjectsEnabled(!initialState)
      })

      // Should update immediately before save completes
      expect(result.current?.projectsEnabled).toBe(!initialState)

      // Complete the save
      await act(async () => {
        resolveUpdate!()
        await updatePromise
      })
    })
  })

  describe('Data Synchronization', () => {
    it('should refresh settings from server', async () => {
      mockGetCredential
        .mockResolvedValueOnce({ value: 'true' })
        .mockResolvedValueOnce({ value: 'false' })

      const { result } = renderHook(() => useSettings(), {
        wrapper: ({ children }) => <SettingsProvider>{children}</SettingsProvider>
      })

      await waitFor(() => {
        expect(result.current?.loading).toBe(false)
        expect(result.current?.projectsEnabled).toBe(true)
      })

      // User or another tab changed the setting
      await act(async () => {
        await result.current?.refreshSettings()
      })

      // Should reflect new value
      expect(result.current?.projectsEnabled).toBe(false)
      expect(mockGetCredential).toHaveBeenCalledTimes(2)
    })

    it('should share state across multiple components', async () => {
      const Component1 = () => {
        const settings = useSettings()
        return (
          <div data-testid="comp1-status">
            {settings?.projectsEnabled ? 'Component1: ON' : 'Component1: OFF'}
          </div>
        )
      }

      const Component2 = () => {
        const settings = useSettings()
        return (
          <div>
            <div data-testid="comp2-status">
              {settings?.projectsEnabled ? 'Component2: ON' : 'Component2: OFF'}
            </div>
            <button 
              onClick={() => settings?.setProjectsEnabled(false)}
              data-testid="disable-btn"
            >
              Disable Projects
            </button>
          </div>
        )
      }

      mockCreateCredential.mockResolvedValueOnce(undefined)

      render(
        <SettingsProvider>
          <Component1 />
          <Component2 />
        </SettingsProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('comp1-status')).toHaveTextContent('Component1: ON')
        expect(screen.getByTestId('comp2-status')).toHaveTextContent('Component2: ON')
      })

      // Update from one component
      act(() => {
        screen.getByTestId('disable-btn').click()
      })

      // Both components should reflect the change
      expect(screen.getByTestId('comp1-status')).toHaveTextContent('Component1: OFF')
      expect(screen.getByTestId('comp2-status')).toHaveTextContent('Component2: OFF')
    })
  })

  describe('Error Boundaries', () => {
    it('should handle missing provider gracefully', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

      const TestComponent = () => {
        try {
          const settings = useSettings()
          return <div>{settings?.projectsEnabled ? 'ON' : 'OFF'}</div>
        } catch (error) {
          return <div>Error: Must use within provider</div>
        }
      }

      // Should handle gracefully when used outside provider
      const { container } = render(<TestComponent />)
      
      // The actual behavior depends on the implementation
      // Either it throws or returns null
      expect(container.textContent).toMatch(/Error|OFF/)

      consoleError.mockRestore()
    })

    it('should handle network errors gracefully', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockGetCredential.mockRejectedValueOnce(new Error('Network timeout'))

      const { result } = renderHook(() => useSettings(), {
        wrapper: ({ children }) => <SettingsProvider>{children}</SettingsProvider>
      })

      await waitFor(() => {
        expect(result.current?.loading).toBe(false)
      })

      // Should use default value on error
      expect(result.current?.projectsEnabled).toBe(true)
      expect(consoleError).toHaveBeenCalledWith(
        'Failed to load settings:',
        expect.any(Error)
      )

      consoleError.mockRestore()
    })
  })

  describe('Performance', () => {
    it('should not reload settings on re-render', async () => {
      mockGetCredential.mockResolvedValue({ value: 'true' })

      const { result, rerender } = renderHook(() => useSettings(), {
        wrapper: ({ children }) => <SettingsProvider>{children}</SettingsProvider>
      })

      await waitFor(() => {
        expect(result.current?.loading).toBe(false)
      })

      const callCount = mockGetCredential.mock.calls.length

      // Re-render multiple times
      rerender()
      rerender()
      rerender()

      // Should not make additional API calls
      expect(mockGetCredential).toHaveBeenCalledTimes(callCount)
    })

    it('should render children immediately without blocking', () => {
      // Simulate slow loading
      mockGetCredential.mockImplementationOnce(
        () => new Promise(() => {}) // Never resolves
      )

      render(
        <SettingsProvider>
          <div data-testid="child">Critical UI Element</div>
        </SettingsProvider>
      )

      // Children should render immediately
      expect(screen.getByTestId('child')).toBeInTheDocument()
      expect(screen.getByTestId('child')).toHaveTextContent('Critical UI Element')
    })
  })
})