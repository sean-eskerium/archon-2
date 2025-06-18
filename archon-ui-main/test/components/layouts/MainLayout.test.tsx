import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MainLayout } from '@/components/layouts/MainLayout'
import { MemoryRouter } from 'react-router-dom'

// Mock dependencies
vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    toggleTheme: vi.fn()
  })
}))

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

vi.mock('@/services/credentialsService', () => ({
  credentialsService: {
    baseUrl: 'http://localhost:8080',
    getAllCredentials: vi.fn()
  }
}))

// Mock child components
vi.mock('@/components/layouts/SideNavigation', () => ({
  SideNavigation: () => <div data-testid="side-navigation">Side Navigation</div>
}))

vi.mock('@/components/layouts/KnowledgeChatPanel', () => ({
  KnowledgeChatPanel: () => <div data-testid="knowledge-chat-panel">Knowledge Chat Panel</div>
}))

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  X: ({ className }: any) => <span className={className} data-testid="close-icon">X</span>
}))

// Mock fetch
global.fetch = vi.fn()

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <MemoryRouter>
      {component}
    </MemoryRouter>
  )
}

describe('MainLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('Layout Structure', () => {
    it('should render main layout structure', () => {
      renderWithRouter(
        <MainLayout>
          <div data-testid="test-content">Test Content</div>
        </MainLayout>
      )

      // Verify layout components
      expect(screen.getByTestId('side-navigation')).toBeInTheDocument()
      expect(screen.getByTestId('test-content')).toBeInTheDocument()
      
      // Verify background grid
      const grid = document.querySelector('.neon-grid')
      expect(grid).toBeInTheDocument()
      expect(grid).toHaveClass('absolute', 'inset-0', 'pointer-events-none')
    })

    it('should render floating navigation with correct positioning', () => {
      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      const navContainer = screen.getByTestId('side-navigation').parentElement
      expect(navContainer).toHaveClass('fixed', 'left-6', 'top-1/2', '-translate-y-1/2', 'z-50')
    })

    it('should render main content area with proper spacing', () => {
      renderWithRouter(
        <MainLayout>
          <div data-testid="content">Content</div>
        </MainLayout>
      )

      const content = screen.getByTestId('content')
      const contentWrapper = content.closest('.min-h-screen')
      expect(contentWrapper).toHaveClass('pt-8', 'pb-16')
      
      // Check left padding for navigation
      const mainArea = content.closest('.pl-\\[100px\\]')
      expect(mainArea).toBeInTheDocument()
    })
  })

  describe('Knowledge Chat Panel', () => {
    it('should show chat button when panel is closed', () => {
      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      const chatButton = screen.getByRole('button', { name: 'Open Knowledge Assistant' })
      expect(chatButton).toBeInTheDocument()
      expect(chatButton).toHaveClass('fixed', 'bottom-6', 'right-6')
      
      // Verify logo image
      const logo = chatButton.querySelector('img')
      expect(logo).toHaveAttribute('src', '/logo-neon.svg')
      expect(logo).toHaveAttribute('alt', 'Archon')
    })

    it('should open chat panel when button is clicked', async () => {
      const user = userEvent.setup({ delay: null })
      
      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      const chatButton = screen.getByRole('button', { name: 'Open Knowledge Assistant' })
      await user.click(chatButton)

      // Chat panel should be visible
      expect(screen.getByTestId('knowledge-chat-panel')).toBeInTheDocument()
      
      // Chat button should be hidden
      expect(chatButton).not.toBeInTheDocument()
      
      // Close button should be visible
      expect(screen.getByRole('button', { name: 'Close Knowledge Assistant' })).toBeInTheDocument()
    })

    it('should close chat panel when close button is clicked', async () => {
      const user = userEvent.setup({ delay: null })
      
      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      // Open chat first
      await user.click(screen.getByRole('button', { name: 'Open Knowledge Assistant' }))
      
      // Then close it
      const closeButton = screen.getByRole('button', { name: 'Close Knowledge Assistant' })
      await user.click(closeButton)

      // Chat button should be visible again
      expect(screen.getByRole('button', { name: 'Open Knowledge Assistant' })).toBeInTheDocument()
      
      // Close button should be hidden
      expect(closeButton).not.toBeInTheDocument()
    })

    it('should animate chat panel slide in/out', async () => {
      const user = userEvent.setup({ delay: null })
      
      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      // Get the chat panel container
      const chatPanel = screen.getByTestId('knowledge-chat-panel').parentElement
      
      // Initially should be translated off-screen
      expect(chatPanel).toHaveStyle({ transform: 'translateX(100%)' })

      // Open chat
      await user.click(screen.getByRole('button', { name: 'Open Knowledge Assistant' }))
      
      // Should slide in
      expect(chatPanel).toHaveStyle({ transform: 'translateX(0)' })
    })
  })

  describe('Backend Health Check', () => {
    it('should check backend health on mount', async () => {
      const mockFetch = vi.mocked(global.fetch)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'healthy' })
      } as any)

      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      // Advance timers to trigger health check
      vi.advanceTimersByTime(1000)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8080/health',
          expect.objectContaining({ method: 'GET' })
        )
      })
    })

    it('should retry backend health check on failure', async () => {
      const mockFetch = vi.mocked(global.fetch)
      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: 'healthy' })
        } as any)

      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      // First attempt
      vi.advanceTimersByTime(1000)
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(1)
      })

      // Retry with exponential backoff
      vi.advanceTimersByTime(1500) // 1000 * 1.5^0
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('OpenAI API Key Check', () => {
    it('should check for OpenAI API key after backend is ready', async () => {
      const mockFetch = vi.mocked(global.fetch)
      const { credentialsService } = await import('@/services/credentialsService')
      const mockGetAllCredentials = vi.mocked(credentialsService.getAllCredentials)
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'healthy' })
      } as any)

      mockGetAllCredentials.mockResolvedValueOnce([
        {
          key: 'OPENAI_API_KEY',
          value: 'sk-test-key',
          is_encrypted: false,
          encrypted_value: null,
          category: 'api_keys'
        }
      ] as any)

      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      // Trigger health check
      vi.advanceTimersByTime(1000)
      
      // Wait for health check to complete and credential check to start
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled()
      })
      
      vi.advanceTimersByTime(500)
      
      await waitFor(() => {
        expect(mockGetAllCredentials).toHaveBeenCalled()
      })
    })

    it('should show warning toast when OpenAI API key is missing', async () => {
      const mockFetch = vi.mocked(global.fetch)
      const { credentialsService } = await import('@/services/credentialsService')
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'healthy' })
      } as any)

      vi.mocked(credentialsService.getAllCredentials).mockResolvedValueOnce([])

      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      // Trigger health check and credential check
      vi.advanceTimersByTime(1000)
      await waitFor(() => expect(mockFetch).toHaveBeenCalled())
      
      vi.advanceTimersByTime(500)
      
      await waitFor(() => {
        expect(showToast).toHaveBeenCalledWith(
          'OpenAI API Key missing! Click here to go to Settings and configure it.',
          'warning',
          8000
        )
      })
    })

    it('should handle encrypted API keys correctly', async () => {
      const mockFetch = vi.mocked(global.fetch)
      const { credentialsService } = await import('@/services/credentialsService')
      const mockGetAllCredentials = vi.mocked(credentialsService.getAllCredentials)
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'healthy' })
      } as any)

      mockGetAllCredentials.mockResolvedValueOnce([
        {
          key: 'OPENAI_API_KEY',
          value: null,
          is_encrypted: true,
          encrypted_value: 'encrypted-value-here',
          category: 'api_keys'
        }
      ] as any)

      const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => {})

      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      // Trigger checks
      vi.advanceTimersByTime(1500)
      
      await waitFor(() => {
        expect(consoleLog).toHaveBeenCalledWith(
          '✅ OpenAI API key is configured'
        )
      })

      consoleLog.mockRestore()
    })
  })

  describe('Error Handling', () => {
    it('should handle credential check errors gracefully', async () => {
      const mockFetch = vi.mocked(global.fetch)
      const { credentialsService } = await import('@/services/credentialsService')
      const consoleError = vi.spyOn(console, 'error').mockImplementation()
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'healthy' })
      } as any)

      vi.mocked(credentialsService.getAllCredentials).mockRejectedValueOnce(
        new Error('Credential service error')
      )

      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      // Trigger checks
      vi.advanceTimersByTime(1500)
      
      await waitFor(() => {
        expect(consoleError).toHaveBeenCalledWith(
          expect.stringContaining('Error checking OpenAI API key'),
          expect.any(Error)
        )
      })

      consoleError.mockRestore()
    })
  })

  describe('Responsive Behavior', () => {
    it('should maintain layout structure on different screen sizes', () => {
      // Mock viewport size
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 640 // Mobile width
      })

      renderWithRouter(
        <MainLayout>
          <div>Mobile Content</div>
        </MainLayout>
      )

      // Main layout elements should still be present
      expect(screen.getByTestId('side-navigation')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Open Knowledge Assistant' })).toBeInTheDocument()
    })
  })

  describe('Theme Integration', () => {
    it('should apply dark theme classes', () => {
      renderWithRouter(
        <MainLayout>
          <div>Content</div>
        </MainLayout>
      )

      // Check for dark theme classes
      const mainContainer = document.querySelector('.dark\\:bg-black')
      expect(mainContainer).toBeInTheDocument()
    })
  })
})