import { describe, it, expect, vi, beforeEach, afterEach, MockedFunction } from 'vitest'
import { render, screen, renderHook, act, waitFor } from '@testing-library/react'
import React from 'react'
import { SettingsProvider, useSettings } from '@/contexts/SettingsContext'
import { credentialsService } from '@/services/credentialsService'

// Mock credentialsService
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
    // Default mock responses
    mockGetCredential.mockRejectedValue(new Error('Not found'))
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('SettingsProvider', () => {
    it('should provide settings context', async () => {
      const TestComponent = () => {
        const settings = useSettings()
        return (
          <div>
            <div>Projects: {settings.projectsEnabled ? 'enabled' : 'disabled'}</div>
            <div>Loading: {settings.loading ? 'yes' : 'no'}</div>
          </div>
        )
      }

      render(
        <SettingsProvider>
          <TestComponent />
        </SettingsProvider>
      )

      await waitFor(() => {
        expect(screen.getByText(/Projects:/)).toBeInTheDocument()
        expect(screen.getByText(/Loading: no/)).toBeInTheDocument()
      })
    })

    it('should load settings on mount', async () => {
      mockGetCredential.mockResolvedValueOnce({ value: 'false' })

      const { result } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      // Initially loading
      expect(result.current.loading).toBe(true)

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
        expect(result.current.projectsEnabled).toBe(false)
      })

      expect(mockGetCredential).toHaveBeenCalledWith('PROJECTS_ENABLED')
    })

    it('should default to projectsEnabled=true when not found', async () => {
      mockGetCredential.mockRejectedValueOnce(new Error('Not found'))

      const { result } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
        expect(result.current.projectsEnabled).toBe(true)
      })
    })

    it('should handle true string value for projectsEnabled', async () => {
      mockGetCredential.mockResolvedValueOnce({ value: 'true' })

      const { result } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      await waitFor(() => {
        expect(result.current.projectsEnabled).toBe(true)
      })
    })
  })

  describe('Settings Updates', () => {
    it('should update projectsEnabled setting', async () => {
      mockCreateCredential.mockResolvedValueOnce(undefined)

      const { result } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Update setting
      await act(async () => {
        await result.current.setProjectsEnabled(false)
      })

      expect(result.current.projectsEnabled).toBe(false)
      expect(mockCreateCredential).toHaveBeenCalledWith({
        key: 'PROJECTS_ENABLED',
        value: 'false',
        is_encrypted: false,
        category: 'features',
        description: 'Enable or disable Projects and Tasks functionality'
      })
    })

    it('should revert on update failure', async () => {
      mockCreateCredential.mockRejectedValueOnce(new Error('Update failed'))

      const { result } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const initialValue = result.current.projectsEnabled

      // Try to update setting
      await expect(async () => {
        await act(async () => {
          await result.current.setProjectsEnabled(!initialValue)
        })
      }).rejects.toThrow('Update failed')

      // Should revert to initial value
      expect(result.current.projectsEnabled).toBe(initialValue)
    })

    it('should update immediately for optimistic UI', async () => {
      let resolveUpdate: () => void
      const updatePromise = new Promise<void>(resolve => {
        resolveUpdate = resolve
      })
      
      mockCreateCredential.mockImplementationOnce(() => updatePromise)

      const { result } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Start update
      const updateComplete = act(async () => {
        await result.current.setProjectsEnabled(false)
      })

      // Should update immediately
      expect(result.current.projectsEnabled).toBe(false)

      // Complete the update
      resolveUpdate!()
      await updateComplete
    })
  })

  describe('Refresh Settings', () => {
    it('should refresh settings when called', async () => {
      mockGetCredential
        .mockResolvedValueOnce({ value: 'true' })
        .mockResolvedValueOnce({ value: 'false' })

      const { result } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
        expect(result.current.projectsEnabled).toBe(true)
      })

      // Refresh settings
      await act(async () => {
        await result.current.refreshSettings()
      })

      expect(result.current.projectsEnabled).toBe(false)
      expect(mockGetCredential).toHaveBeenCalledTimes(2)
    })
  })

  describe('Error Handling', () => {
    it('should handle load errors gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockGetCredential.mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
        expect(result.current.projectsEnabled).toBe(true) // Default value
      })

      expect(consoleSpy).toHaveBeenCalledWith('Failed to load settings:', expect.any(Error))
      consoleSpy.mockRestore()
    })

    it('should throw error when useSettings used outside provider', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const TestComponent = () => {
        const settings = useSettings()
        return <div>{settings.projectsEnabled}</div>
      }

      expect(() => {
        render(<TestComponent />)
      }).toThrow('useSettings must be used within a SettingsProvider')

      consoleSpy.mockRestore()
    })

    it('should handle undefined credential values', async () => {
      mockGetCredential.mockResolvedValueOnce({ value: undefined })

      const { result } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
        expect(result.current.projectsEnabled).toBe(true) // Default
      })
    })
  })

  describe('Loading State', () => {
    it('should show loading state during initial load', async () => {
      let resolveLoad: () => void
      const loadPromise = new Promise<{ value: string }>(resolve => {
        resolveLoad = () => resolve({ value: 'true' })
      })

      mockGetCredential.mockReturnValueOnce(loadPromise)

      const { result } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      // Should be loading
      expect(result.current.loading).toBe(true)

      // Resolve load
      await act(async () => {
        resolveLoad!()
        await loadPromise
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
    })

    it('should not reload on re-render', async () => {
      mockGetCredential.mockResolvedValue({ value: 'true' })

      const { result, rerender } = renderHook(() => useSettings(), {
        wrapper: SettingsProvider
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(mockGetCredential).toHaveBeenCalledTimes(1)

      // Re-render
      rerender()

      // Should not call again
      expect(mockGetCredential).toHaveBeenCalledTimes(1)
    })
  })

  describe('Multiple Components', () => {
    it('should share settings across components', async () => {
      const TestComponent1 = () => {
        const { projectsEnabled } = useSettings()
        return <div data-testid="comp1">{projectsEnabled ? 'on' : 'off'}</div>
      }

      const TestComponent2 = () => {
        const { projectsEnabled, setProjectsEnabled } = useSettings()
        return (
          <div>
            <div data-testid="comp2">{projectsEnabled ? 'on' : 'off'}</div>
            <button onClick={() => setProjectsEnabled(false)}>Disable</button>
          </div>
        )
      }

      render(
        <SettingsProvider>
          <TestComponent1 />
          <TestComponent2 />
        </SettingsProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('comp1')).toHaveTextContent('on')
        expect(screen.getByTestId('comp2')).toHaveTextContent('on')
      })

      // Update from one component
      mockCreateCredential.mockResolvedValueOnce(undefined)
      
      await act(async () => {
        screen.getByText('Disable').click()
      })

      // Both should update
      expect(screen.getByTestId('comp1')).toHaveTextContent('off')
      expect(screen.getByTestId('comp2')).toHaveTextContent('off')
    })
  })

  describe('Children Rendering', () => {
    it('should render children', () => {
      render(
        <SettingsProvider>
          <div data-testid="child">Child Component</div>
        </SettingsProvider>
      )

      expect(screen.getByTestId('child')).toBeInTheDocument()
    })

    it('should not block render during loading', () => {
      // Make loading take longer
      mockGetCredential.mockImplementationOnce(() => new Promise(() => {}))

      render(
        <SettingsProvider>
          <div data-testid="child">Should render immediately</div>
        </SettingsProvider>
      )

      expect(screen.getByTestId('child')).toBeInTheDocument()
    })
  })
})