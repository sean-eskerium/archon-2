import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RAGSettings } from '@/components/settings/RAGSettings'
import { credentialsService } from '@/services/credentialsService'

// Mock dependencies
vi.mock('@/services/credentialsService')
vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  Settings: ({ className }: any) => <span className={className} data-testid="settings-icon">⚙️</span>,
  Check: ({ className }: any) => <span className={className} data-testid="check-icon">✓</span>,
  Save: ({ className }: any) => <span className={className} data-testid="save-icon">💾</span>,
  Loader: ({ className }: any) => <span className={className} data-testid="loader-icon">⌛</span>
}))

describe('RAGSettings', () => {
  const mockRagSettings = {
    MODEL_CHOICE: 'gpt-4',
    USE_CONTEXTUAL_EMBEDDINGS: false,
    CONTEXTUAL_EMBEDDINGS_MAX_WORKERS: 3,
    USE_HYBRID_SEARCH: true,
    USE_AGENTIC_RAG: false,
    USE_RERANKING: true
  }

  const defaultProps = {
    ragSettings: mockRagSettings,
    setRagSettings: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(credentialsService.updateRagSettings).mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Display', () => {
    it('should display RAG configuration', () => {
      render(<RAGSettings {...defaultProps} />)

      expect(screen.getByText('RAG Settings')).toBeInTheDocument()
      expect(screen.getByText(/Configure Retrieval-Augmented Generation/)).toBeInTheDocument()
    })

    it('should display model choice input', () => {
      render(<RAGSettings {...defaultProps} />)

      const modelInput = screen.getByLabelText('LLM Model - LLM for summaries and contextual embeddings')
      expect(modelInput).toBeInTheDocument()
      expect(modelInput).toHaveValue('gpt-4')
    })

    it('should display all toggle options', () => {
      render(<RAGSettings {...defaultProps} />)

      expect(screen.getByText('Use Contextual Embeddings')).toBeInTheDocument()
      expect(screen.getByText('Use Hybrid Search')).toBeInTheDocument()
      expect(screen.getByText('Use Agentic RAG')).toBeInTheDocument()
      expect(screen.getByText('Use Reranking')).toBeInTheDocument()
    })

    it('should display descriptions for each option', () => {
      render(<RAGSettings {...defaultProps} />)

      expect(screen.getByText(/Enhances embeddings with contextual information/)).toBeInTheDocument()
      expect(screen.getByText(/Combines vector similarity search with keyword search/)).toBeInTheDocument()
      expect(screen.getByText(/Enables code example extraction/)).toBeInTheDocument()
      expect(screen.getByText(/Applies cross-encoder reranking/)).toBeInTheDocument()
    })
  })

  describe('Model Configuration', () => {
    it('should update model choice', async () => {
      const user = userEvent.setup()
      const setRagSettings = vi.fn()
      
      render(<RAGSettings {...defaultProps} setRagSettings={setRagSettings} />)

      const modelInput = screen.getByLabelText('LLM Model - LLM for summaries and contextual embeddings')
      await user.clear(modelInput)
      await user.type(modelInput, 'gpt-4-turbo')

      expect(setRagSettings).toHaveBeenLastCalledWith({
        ...mockRagSettings,
        MODEL_CHOICE: 'gpt-4-turbo'
      })
    })
  })

  describe('Toggle Settings', () => {
    it('should toggle contextual embeddings', async () => {
      const user = userEvent.setup()
      const setRagSettings = vi.fn()
      
      render(<RAGSettings {...defaultProps} setRagSettings={setRagSettings} />)

      const checkbox = screen.getByLabelText('Use Contextual Embeddings')
      await user.click(checkbox)

      expect(setRagSettings).toHaveBeenCalledWith({
        ...mockRagSettings,
        USE_CONTEXTUAL_EMBEDDINGS: true
      })
    })

    it('should show max workers input when contextual embeddings enabled', () => {
      const settingsWithContextual = {
        ...mockRagSettings,
        USE_CONTEXTUAL_EMBEDDINGS: true
      }
      
      render(<RAGSettings {...defaultProps} ragSettings={settingsWithContextual} />)

      expect(screen.getByText('Max Workers')).toBeInTheDocument()
      const workersInput = screen.getByDisplayValue('3')
      expect(workersInput).toBeInTheDocument()
      expect(workersInput).toHaveAttribute('type', 'number')
      expect(workersInput).toHaveAttribute('min', '1')
      expect(workersInput).toHaveAttribute('max', '20')
    })

    it('should update max workers', async () => {
      const user = userEvent.setup()
      const setRagSettings = vi.fn()
      const settingsWithContextual = {
        ...mockRagSettings,
        USE_CONTEXTUAL_EMBEDDINGS: true
      }
      
      render(
        <RAGSettings 
          ragSettings={settingsWithContextual} 
          setRagSettings={setRagSettings} 
        />
      )

      const workersInput = screen.getByDisplayValue('3')
      await user.clear(workersInput)
      await user.type(workersInput, '5')

      expect(setRagSettings).toHaveBeenCalledWith({
        ...settingsWithContextual,
        CONTEXTUAL_EMBEDDINGS_MAX_WORKERS: 5
      })
    })

    it('should toggle hybrid search', async () => {
      const user = userEvent.setup()
      const setRagSettings = vi.fn()
      
      render(<RAGSettings {...defaultProps} setRagSettings={setRagSettings} />)

      const checkbox = screen.getByLabelText('Use Hybrid Search')
      await user.click(checkbox)

      expect(setRagSettings).toHaveBeenCalledWith({
        ...mockRagSettings,
        USE_HYBRID_SEARCH: false
      })
    })

    it('should toggle agentic RAG', async () => {
      const user = userEvent.setup()
      const setRagSettings = vi.fn()
      
      render(<RAGSettings {...defaultProps} setRagSettings={setRagSettings} />)

      const checkbox = screen.getByLabelText('Use Agentic RAG')
      await user.click(checkbox)

      expect(setRagSettings).toHaveBeenCalledWith({
        ...mockRagSettings,
        USE_AGENTIC_RAG: true
      })
    })

    it('should toggle reranking', async () => {
      const user = userEvent.setup()
      const setRagSettings = vi.fn()
      
      render(<RAGSettings {...defaultProps} setRagSettings={setRagSettings} />)

      const checkbox = screen.getByLabelText('Use Reranking')
      await user.click(checkbox)

      expect(setRagSettings).toHaveBeenCalledWith({
        ...mockRagSettings,
        USE_RERANKING: false
      })
    })
  })

  describe('Save Functionality', () => {
    it('should save settings successfully', async () => {
      const user = userEvent.setup()
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })
      
      render(<RAGSettings {...defaultProps} />)

      const saveButton = screen.getByText('Save Settings')
      await user.click(saveButton)

      expect(credentialsService.updateRagSettings).toHaveBeenCalledWith(mockRagSettings)
      
      await waitFor(() => {
        expect(showToast).toHaveBeenCalledWith('RAG settings saved successfully!', 'success')
      })
    })

    it('should show loading state while saving', async () => {
      const user = userEvent.setup()
      let resolvePromise: () => void
      const savePromise = new Promise<void>(resolve => {
        resolvePromise = resolve
      })
      
      vi.mocked(credentialsService.updateRagSettings).mockReturnValue(savePromise)
      
      render(<RAGSettings {...defaultProps} />)

      const saveButton = screen.getByText('Save Settings')
      await user.click(saveButton)

      // Should show loading state
      expect(screen.getByText('Saving...')).toBeInTheDocument()
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument()
      expect(saveButton).toBeDisabled()

      // Resolve the promise
      resolvePromise!()
      
      // Should return to normal state
      await waitFor(() => {
        expect(screen.getByText('Save Settings')).toBeInTheDocument()
        expect(saveButton).not.toBeDisabled()
      })
    })

    it('should handle save errors', async () => {
      const user = userEvent.setup()
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })
      
      vi.mocked(credentialsService.updateRagSettings).mockRejectedValue(new Error('Network error'))
      
      render(<RAGSettings {...defaultProps} />)

      const saveButton = screen.getByText('Save Settings')
      await user.click(saveButton)

      await waitFor(() => {
        expect(showToast).toHaveBeenCalledWith('Failed to save settings', 'error')
      })
    })
  })

  describe('Checkbox Behavior', () => {
    it('should show check icon when checked', () => {
      render(<RAGSettings {...defaultProps} />)

      // Hybrid search is checked in mock data
      const hybridSearchContainer = screen.getByText('Use Hybrid Search').closest('.group')
      const checkIcon = hybridSearchContainer?.querySelector('[data-testid="check-icon"]')
      
      expect(checkIcon).toHaveClass('opacity-100')
    })

    it('should hide check icon when unchecked', () => {
      render(<RAGSettings {...defaultProps} />)

      // Agentic RAG is unchecked in mock data
      const agenticRagContainer = screen.getByText('Use Agentic RAG').closest('.group')
      const checkIcon = agenticRagContainer?.querySelector('[data-testid="check-icon"]')
      
      expect(checkIcon).toHaveClass('opacity-0')
    })

    it('should apply correct styling to checked checkboxes', () => {
      render(<RAGSettings {...defaultProps} />)

      const hybridSearchCheckbox = screen.getByLabelText('Use Hybrid Search')
      const label = hybridSearchCheckbox.nextElementSibling

      expect(label).toHaveClass('peer-checked:border-green-500')
      expect(label).toHaveClass('peer-checked:shadow-[0_0_10px_rgba(34,197,94,0.2)]')
    })
  })

  describe('Validation', () => {
    it('should validate max workers within range', async () => {
      const user = userEvent.setup()
      const setRagSettings = vi.fn()
      const settingsWithContextual = {
        ...mockRagSettings,
        USE_CONTEXTUAL_EMBEDDINGS: true
      }
      
      render(
        <RAGSettings 
          ragSettings={settingsWithContextual} 
          setRagSettings={setRagSettings} 
        />
      )

      const workersInput = screen.getByDisplayValue('3')
      
      // Try to set invalid value
      await user.clear(workersInput)
      await user.type(workersInput, '0')

      // Should default to 3 when parsing fails or value is invalid
      expect(setRagSettings).toHaveBeenCalledWith({
        ...settingsWithContextual,
        CONTEXTUAL_EMBEDDINGS_MAX_WORKERS: 3
      })
    })
  })
})