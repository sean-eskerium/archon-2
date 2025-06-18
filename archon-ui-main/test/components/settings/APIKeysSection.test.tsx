import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { APIKeysSection } from '@/components/settings/APIKeysSection'
import { credentialsService } from '@/services/credentialsService'
import type { Credential } from '@/services/credentialsService'

// Mock dependencies
vi.mock('@/services/credentialsService')
vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  Key: ({ className }: any) => <span className={className} data-testid="key-icon">🔑</span>,
  Plus: ({ className }: any) => <span className={className} data-testid="plus-icon">➕</span>,
  Trash2: ({ className }: any) => <span className={className} data-testid="trash-icon">🗑</span>,
  Check: ({ className }: any) => <span className={className} data-testid="check-icon">✓</span>,
  Save: ({ className }: any) => <span className={className} data-testid="save-icon">💾</span>,
  Lock: ({ className }: any) => <span className={className} data-testid="lock-icon">🔒</span>,
  Unlock: ({ className }: any) => <span className={className} data-testid="unlock-icon">🔓</span>
}))

describe('APIKeysSection', () => {
  const mockCredentials: Credential[] = [
    {
      key: 'OPENAI_API_KEY',
      value: 'sk-test123456789',
      description: 'OpenAI API Key',
      is_encrypted: false,
      category: 'api_keys',
      created_at: new Date('2024-01-01'),
      updated_at: new Date('2024-01-01')
    },
    {
      key: 'ANTHROPIC_API_KEY',
      value: '',
      encrypted_value: 'encrypted_value_here',
      description: 'Anthropic API Key',
      is_encrypted: true,
      category: 'api_keys',
      created_at: new Date('2024-01-02'),
      updated_at: new Date('2024-01-02')
    },
    {
      key: 'CUSTOM_KEY',
      value: 'custom-value',
      description: 'Custom credential',
      is_encrypted: false,
      category: 'custom',
      created_at: new Date('2024-01-03'),
      updated_at: new Date('2024-01-03')
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    // Default mock implementations
    vi.mocked(credentialsService.getAllCredentials).mockResolvedValue(mockCredentials)
    vi.mocked(credentialsService.getCredentialsByCategory).mockImplementation(async (category) => {
      return mockCredentials.filter(cred => cred.category === category)
    })
    vi.mocked(credentialsService.createCredential).mockImplementation(async (cred) => ({
      ...cred,
      created_at: new Date(),
      updated_at: new Date()
    }))
    vi.mocked(credentialsService.updateCredential).mockResolvedValue(undefined)
    vi.mocked(credentialsService.deleteCredential).mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Display and Loading', () => {
    it('should display API key fields after loading', async () => {
      render(<APIKeysSection />)

      // Initially shows loading
      expect(screen.getByText('API Keys')).toBeInTheDocument()
      
      // Wait for credentials to load
      await waitFor(() => {
        expect(screen.getByLabelText('OPENAI_API_KEY')).toBeInTheDocument()
      })

      expect(screen.getByLabelText('ANTHROPIC_API_KEY')).toBeInTheDocument()
      expect(screen.getByLabelText('CUSTOM_KEY')).toBeInTheDocument()
    })

    it('should show loading state initially', () => {
      render(<APIKeysSection />)

      // Should show loading skeleton
      const loadingElements = document.querySelectorAll('.animate-pulse')
      expect(loadingElements.length).toBeGreaterThan(0)
    })

    it('should handle loading errors', async () => {
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })
      
      vi.mocked(credentialsService.getAllCredentials).mockRejectedValue(new Error('Network error'))

      render(<APIKeysSection />)

      await waitFor(() => {
        expect(showToast).toHaveBeenCalledWith('Failed to load credentials', 'error')
      })
    })

    it('should display description text', async () => {
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByText(/Manage your API keys and credentials/)).toBeInTheDocument()
      })
    })
  })

  describe('Value Masking', () => {
    it('should mask sensitive values by default', async () => {
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByLabelText('OPENAI_API_KEY')).toBeInTheDocument()
      })

      const openAIInput = screen.getByLabelText('OPENAI_API_KEY') as HTMLInputElement
      expect(openAIInput.type).toBe('password')
    })

    it('should toggle value visibility', async () => {
      const user = userEvent.setup()
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByText('Show Keys')).toBeInTheDocument()
      })

      // Click show keys button
      await user.click(screen.getByText('Show Keys'))

      const openAIInput = screen.getByLabelText('OPENAI_API_KEY') as HTMLInputElement
      expect(openAIInput.type).toBe('text')
      expect(screen.getByText('Hide Keys')).toBeInTheDocument()
    })

    it('should show placeholder for encrypted credentials', async () => {
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByLabelText('ANTHROPIC_API_KEY')).toBeInTheDocument()
      })

      const encryptedInput = screen.getByLabelText('ANTHROPIC_API_KEY') as HTMLInputElement
      expect(encryptedInput.placeholder).toContain('encrypted - enter new value to update')
    })
  })

  describe('Update Functionality', () => {
    it('should update API keys', async () => {
      const user = userEvent.setup()
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByLabelText('OPENAI_API_KEY')).toBeInTheDocument()
      })

      const input = screen.getByLabelText('OPENAI_API_KEY') as HTMLInputElement
      
      // Change value
      await user.clear(input)
      await user.type(input, 'sk-new-key-123')

      // Save button should appear
      const saveButton = screen.getByTestId('save-icon').parentElement
      expect(saveButton).toBeInTheDocument()
      
      await user.click(saveButton!)

      expect(credentialsService.updateCredential).toHaveBeenCalledWith({
        key: 'OPENAI_API_KEY',
        value: 'sk-new-key-123',
        description: '',
        is_encrypted: false,
        category: 'api_keys'
      })
    })

    it('should save on Enter key press', async () => {
      const user = userEvent.setup()
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByLabelText('OPENAI_API_KEY')).toBeInTheDocument()
      })

      const input = screen.getByLabelText('OPENAI_API_KEY') as HTMLInputElement
      
      await user.clear(input)
      await user.type(input, 'sk-new-key-123{Enter}')

      expect(credentialsService.updateCredential).toHaveBeenCalled()
    })

    it('should show save confirmation', async () => {
      const user = userEvent.setup()
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })

      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByLabelText('OPENAI_API_KEY')).toBeInTheDocument()
      })

      const input = screen.getByLabelText('OPENAI_API_KEY')
      await user.clear(input)
      await user.type(input, 'new-value{Enter}')

      await waitFor(() => {
        expect(showToast).toHaveBeenCalledWith('OPENAI_API_KEY saved successfully!', 'success')
      })
    })

    it('should handle save errors', async () => {
      const user = userEvent.setup()
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })
      
      vi.mocked(credentialsService.updateCredential).mockRejectedValue(new Error('Save failed'))

      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByLabelText('OPENAI_API_KEY')).toBeInTheDocument()
      })

      const input = screen.getByLabelText('OPENAI_API_KEY')
      await user.clear(input)
      await user.type(input, 'new-value{Enter}')

      await waitFor(() => {
        expect(showToast).toHaveBeenCalledWith('Failed to save OPENAI_API_KEY', 'error')
      })
    })
  })

  describe('Add New Credential', () => {
    it('should add new credential', async () => {
      const user = userEvent.setup()
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByText('Add Custom Credential')).toBeInTheDocument()
      })

      // Fill in new credential form
      const keyInput = screen.getByPlaceholderText('e.g., ANTHROPIC_API_KEY')
      const valueInput = screen.getByPlaceholderText('Enter value')
      const descInput = screen.getByPlaceholderText('What is this credential for?')

      await user.type(keyInput, 'NEW_API_KEY')
      await user.type(valueInput, 'new-secret-value')
      await user.type(descInput, 'New API key for testing')

      // Add credential
      await user.click(screen.getByText('Add Credential'))

      expect(credentialsService.createCredential).toHaveBeenCalledWith({
        key: 'NEW_API_KEY',
        value: 'new-secret-value',
        description: 'New API key for testing',
        is_encrypted: false,
        category: 'api_keys'
      })
    })

    it('should toggle encryption for new credentials', async () => {
      const user = userEvent.setup()
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByText('Add Custom Credential')).toBeInTheDocument()
      })

      // Toggle encryption
      const encryptButton = screen.getByTitle('Not secret (plain text)')
      await user.click(encryptButton)
      
      expect(screen.getByTitle('Secret (encrypted)')).toBeInTheDocument()

      // Fill and add
      await user.type(screen.getByPlaceholderText('e.g., ANTHROPIC_API_KEY'), 'SECRET_KEY')
      await user.type(screen.getByPlaceholderText('Enter value'), 'secret-value')
      await user.click(screen.getByText('Add Credential'))

      expect(credentialsService.createCredential).toHaveBeenCalledWith(
        expect.objectContaining({
          is_encrypted: true
        })
      )
    })

    it('should validate key format - require key name', async () => {
      const user = userEvent.setup()
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByText('Add Custom Credential')).toBeInTheDocument()
      })

      const addButton = screen.getByText('Add Credential')
      
      // Button should be disabled without key name
      expect(addButton).toBeDisabled()

      // Type key name
      await user.type(screen.getByPlaceholderText('e.g., ANTHROPIC_API_KEY'), 'TEST_KEY')
      
      // Button should now be enabled
      expect(addButton).not.toBeDisabled()
    })
  })

  describe('Delete Functionality', () => {
    it('should delete API keys', async () => {
      const user = userEvent.setup()
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })

      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByLabelText('CUSTOM_KEY')).toBeInTheDocument()
      })

      // Find delete button for CUSTOM_KEY (should be visible when no changes)
      const deleteButtons = screen.getAllByTestId('trash-icon')
      const customKeyDelete = deleteButtons[deleteButtons.length - 1].parentElement
      
      await user.click(customKeyDelete!)

      expect(credentialsService.deleteCredential).toHaveBeenCalledWith('CUSTOM_KEY')
      
      await waitFor(() => {
        expect(showToast).toHaveBeenCalledWith('Credential CUSTOM_KEY deleted successfully!', 'success')
      })
    })

    it('should handle delete errors', async () => {
      const user = userEvent.setup()
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })
      
      vi.mocked(credentialsService.deleteCredential).mockRejectedValue(new Error('Delete failed'))

      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByLabelText('CUSTOM_KEY')).toBeInTheDocument()
      })

      const deleteButtons = screen.getAllByTestId('trash-icon')
      await user.click(deleteButtons[deleteButtons.length - 1].parentElement!)

      await waitFor(() => {
        expect(showToast).toHaveBeenCalledWith('Failed to delete credential', 'error')
      })
    })
  })

  describe('Feature Filtering', () => {
    it('should display feature filter buttons', async () => {
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByText('Core')).toBeInTheDocument()
      })

      // Currently only Core is available
      const coreButton = screen.getByText('Core')
      expect(coreButton).toHaveClass('bg-pink-100')
    })
  })

  describe('Security Notice', () => {
    it('should display security information', async () => {
      render(<APIKeysSection />)

      await waitFor(() => {
        expect(screen.getByText(/Use the Secret toggle when adding credentials/)).toBeInTheDocument()
      })

      expect(screen.getByText(/Press.*Enter.*or click the green save button/)).toBeInTheDocument()
    })
  })
})