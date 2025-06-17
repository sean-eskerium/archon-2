import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SettingsPage } from '@/pages/SettingsPage'
import { credentialsService } from '@/services/credentialsService'
import type { RagSettings } from '@/services/credentialsService'

// Mock dependencies
vi.mock('@/services/credentialsService')
vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))
vi.mock('@/contexts/SettingsContext', () => ({
  useSettings: () => ({
    projectsEnabled: true,
    setProjectsEnabled: vi.fn()
  })
}))

// Mock child components to simplify testing
vi.mock('@/components/settings/FeaturesSection', () => ({
  FeaturesSection: () => <div data-testid="features-section">Features Section</div>
}))
vi.mock('@/components/settings/APIKeysSection', () => ({
  APIKeysSection: () => <div data-testid="api-keys-section">API Keys Section</div>
}))
vi.mock('@/components/settings/RAGSettings', () => ({
  RAGSettings: ({ ragSettings, setRagSettings }: any) => (
    <div data-testid="rag-settings">
      <h3>RAG Settings</h3>
      <label>
        <input
          type="checkbox"
          checked={ragSettings.USE_CONTEXTUAL_EMBEDDINGS}
          onChange={(e) => setRagSettings({
            ...ragSettings,
            USE_CONTEXTUAL_EMBEDDINGS: e.target.checked
          })}
          data-testid="contextual-embeddings-toggle"
        />
        Use Contextual Embeddings
      </label>
      <label>
        <input
          type="number"
          value={ragSettings.CONTEXTUAL_EMBEDDINGS_MAX_WORKERS}
          onChange={(e) => setRagSettings({
            ...ragSettings,
            CONTEXTUAL_EMBEDDINGS_MAX_WORKERS: parseInt(e.target.value)
          })}
          data-testid="max-workers-input"
        />
        Max Workers
      </label>
    </div>
  )
}))
vi.mock('@/components/settings/TestStatus', () => ({
  TestStatus: () => <div data-testid="test-status">Test Status</div>
}))
vi.mock('@/components/settings/IDEGlobalRules', () => ({
  IDEGlobalRules: () => <div data-testid="ide-global-rules">IDE Global Rules</div>
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>
  }
}))

// Mock hooks
vi.mock('@/hooks/useStaggeredEntrance', () => ({
  useStaggeredEntrance: () => ({
    isVisible: true,
    containerVariants: {},
    itemVariants: {},
    titleVariants: {}
  })
}))

describe('SettingsPage', () => {
  const mockRagSettings: RagSettings = {
    USE_CONTEXTUAL_EMBEDDINGS: false,
    CONTEXTUAL_EMBEDDINGS_MAX_WORKERS: 3,
    USE_HYBRID_SEARCH: false,
    USE_AGENTIC_RAG: false,
    USE_RERANKING: false,
    MODEL_CHOICE: 'gpt-4.1-nano'
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Loading and Display', () => {
    it('should load and display current settings', async () => {
      vi.mocked(credentialsService.getRagSettings).mockResolvedValueOnce(mockRagSettings)

      render(<SettingsPage />)

      // Initially shows loading spinner
      expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument()

      // Wait for settings to load
      await waitFor(() => {
        expect(screen.getByText('Settings')).toBeInTheDocument()
      })

      // Verify all sections are rendered
      expect(screen.getByTestId('features-section')).toBeInTheDocument()
      expect(screen.getByTestId('api-keys-section')).toBeInTheDocument()
      expect(screen.getByTestId('rag-settings')).toBeInTheDocument()
      expect(screen.getByTestId('test-status')).toBeInTheDocument()
      expect(screen.getByTestId('ide-global-rules')).toBeInTheDocument()

      // Verify getRagSettings was called
      expect(credentialsService.getRagSettings).toHaveBeenCalledOnce()
    })

    it('should show loading state while fetching settings', () => {
      // Keep promise pending
      vi.mocked(credentialsService.getRagSettings).mockImplementation(
        () => new Promise(() => {})
      )

      render(<SettingsPage />)

      // Should show loading spinner
      const spinner = screen.getByRole('img', { hidden: true })
      expect(spinner).toHaveClass('animate-spin')
    })

    it('should display page header', async () => {
      vi.mocked(credentialsService.getRagSettings).mockResolvedValueOnce(mockRagSettings)

      render(<SettingsPage />)

      await waitFor(() => {
        const heading = screen.getByRole('heading', { name: 'Settings' })
        expect(heading).toBeInTheDocument()
        expect(heading).toHaveClass('text-3xl', 'font-bold')
      })
    })
  })

  describe('RAG Settings Updates', () => {
    it('should update RAG settings state when changed', async () => {
      vi.mocked(credentialsService.getRagSettings).mockResolvedValueOnce(mockRagSettings)
      const user = userEvent.setup()

      render(<SettingsPage />)

      await waitFor(() => {
        expect(screen.getByTestId('rag-settings')).toBeInTheDocument()
      })

      // Toggle contextual embeddings
      const toggle = screen.getByTestId('contextual-embeddings-toggle')
      expect(toggle).not.toBeChecked()

      await user.click(toggle)
      expect(toggle).toBeChecked()

      // Update max workers
      const workersInput = screen.getByTestId('max-workers-input')
      expect(workersInput).toHaveValue(3)

      await user.clear(workersInput)
      await user.type(workersInput, '5')
      expect(workersInput).toHaveValue(5)
    })
  })

  describe('Error Handling', () => {
    it('should handle load errors gracefully', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation()
      vi.mocked(credentialsService.getRagSettings).mockRejectedValueOnce(
        new Error('Network error')
      )

      render(<SettingsPage />)

      await waitFor(() => {
        expect(screen.getByText('Failed to load settings')).toBeInTheDocument()
      })

      // Error should be displayed
      const errorElement = screen.getByText('Failed to load settings')
      expect(errorElement.parentElement).toHaveClass('bg-red-50')

      expect(consoleError).toHaveBeenCalledWith(expect.any(Error))
      consoleError.mockRestore()
    })

    it('should show error in toast notification', async () => {
      const showToast = vi.fn()
      vi.mock('@/contexts/ToastContext', () => ({
        useToast: () => ({ showToast })
      }))

      vi.mocked(credentialsService.getRagSettings).mockRejectedValueOnce(
        new Error('API error')
      )

      render(<SettingsPage />)

      await waitFor(() => {
        expect(showToast).toHaveBeenCalledWith('Failed to load settings', 'error')
      })
    })
  })

  describe('Layout and Responsiveness', () => {
    it('should use two-column layout on large screens', async () => {
      vi.mocked(credentialsService.getRagSettings).mockResolvedValueOnce(mockRagSettings)

      render(<SettingsPage />)

      await waitFor(() => {
        expect(screen.getByText('Settings')).toBeInTheDocument()
      })

      // Find the main grid container
      const mainContent = screen.getByTestId('features-section').parentElement?.parentElement
      expect(mainContent).toHaveClass('grid', 'grid-cols-1', 'lg:grid-cols-2')
    })

    it('should render all sections in correct columns', async () => {
      vi.mocked(credentialsService.getRagSettings).mockResolvedValueOnce(mockRagSettings)

      render(<SettingsPage />)

      await waitFor(() => {
        expect(screen.getByText('Settings')).toBeInTheDocument()
      })

      // Left column should have Features, RAG Settings, and IDE Rules
      const leftColumn = screen.getByTestId('features-section').parentElement
      expect(leftColumn).toContainElement(screen.getByTestId('features-section'))
      expect(leftColumn).toContainElement(screen.getByTestId('rag-settings'))
      expect(leftColumn).toContainElement(screen.getByTestId('ide-global-rules'))

      // Right column should have API Keys and Test Status
      const rightColumn = screen.getByTestId('api-keys-section').parentElement
      expect(rightColumn).toContainElement(screen.getByTestId('api-keys-section'))
      expect(rightColumn).toContainElement(screen.getByTestId('test-status'))
    })
  })

  describe('Conditional Rendering', () => {
    it('should conditionally render IDE Global Rules based on projectsEnabled', async () => {
      vi.mocked(credentialsService.getRagSettings).mockResolvedValueOnce(mockRagSettings)

      // Test with projectsEnabled = true (default mock)
      const { rerender } = render(<SettingsPage />)

      await waitFor(() => {
        expect(screen.getByTestId('ide-global-rules')).toBeInTheDocument()
      })

      // Update mock to disable projects
      vi.mock('@/contexts/SettingsContext', () => ({
        useSettings: () => ({
          projectsEnabled: false,
          setProjectsEnabled: vi.fn()
        })
      }))

      rerender(<SettingsPage />)

      // IDE Global Rules should not be rendered when projects are disabled
      expect(screen.queryByTestId('ide-global-rules')).not.toBeInTheDocument()
    })
  })

  describe('Component Integration', () => {
    it('should pass correct props to RAGSettings component', async () => {
      vi.mocked(credentialsService.getRagSettings).mockResolvedValueOnce(mockRagSettings)

      render(<SettingsPage />)

      await waitFor(() => {
        expect(screen.getByTestId('rag-settings')).toBeInTheDocument()
      })

      // Verify initial state matches loaded settings
      const embeddingsToggle = screen.getByTestId('contextual-embeddings-toggle')
      const workersInput = screen.getByTestId('max-workers-input')

      expect(embeddingsToggle).not.toBeChecked()
      expect(workersInput).toHaveValue(3)
    })
  })

  describe('Animations', () => {
    it('should use staggered entrance animation', async () => {
      const mockStaggeredEntrance = {
        isVisible: true,
        containerVariants: { test: 'container' },
        itemVariants: { test: 'item' },
        titleVariants: { test: 'title' }
      }

      vi.mock('@/hooks/useStaggeredEntrance', () => ({
        useStaggeredEntrance: vi.fn(() => mockStaggeredEntrance)
      }))

      vi.mocked(credentialsService.getRagSettings).mockResolvedValueOnce(mockRagSettings)

      render(<SettingsPage />)

      await waitFor(() => {
        expect(screen.getByText('Settings')).toBeInTheDocument()
      })

      // Verify staggered entrance hook is called with correct parameters
      const { useStaggeredEntrance } = await import('@/hooks/useStaggeredEntrance')
      expect(useStaggeredEntrance).toHaveBeenCalledWith([1, 2, 3, 4], 0.15)
    })
  })
})