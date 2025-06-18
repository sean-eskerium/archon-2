import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TestStatus } from '@/components/settings/TestStatus'
import { testService } from '@/services/testService'
import type { TestExecution, TestStreamMessage } from '@/services/testService'

// Mock dependencies
vi.mock('@/services/testService')
vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  Terminal: ({ className }: any) => <span className={className} data-testid="terminal-icon">💻</span>,
  RefreshCw: ({ className }: any) => <span className={className} data-testid="refresh-icon">↻</span>,
  Play: ({ className }: any) => <span className={className} data-testid="play-icon">▶</span>,
  Square: ({ className }: any) => <span className={className} data-testid="square-icon">◼</span>,
  Clock: ({ className }: any) => <span className={className} data-testid="clock-icon">🕐</span>,
  CheckCircle: ({ className }: any) => <span className={className} data-testid="check-circle-icon">✅</span>,
  XCircle: ({ className }: any) => <span className={className} data-testid="x-circle-icon">❌</span>,
  FileText: ({ className }: any) => <span className={className} data-testid="file-text-icon">📄</span>,
  ChevronUp: ({ className }: any) => <span className={className} data-testid="chevron-up-icon">⌃</span>
}))

describe('TestStatus', () => {
  const mockExecution: TestExecution = {
    execution_id: 'test-123',
    test_type: 'mcp',
    status: 'running',
    start_time: '2024-01-01T00:00:00Z'
  }

  let streamCallbacks: {
    onMessage?: (message: TestStreamMessage) => void
    onError?: (error: Error) => void
    onClose?: (event: CloseEvent) => void
  } = {}

  beforeEach(() => {
    vi.clearAllMocks()
    streamCallbacks = {}
    
    // Mock test service methods
    vi.mocked(testService.runMCPTests).mockResolvedValue(mockExecution)
    vi.mocked(testService.runUITestsWithStreaming).mockImplementation(async (onMessage, onError, onClose) => {
      streamCallbacks.onMessage = onMessage
      streamCallbacks.onError = onError
      streamCallbacks.onClose = onClose
      return 'ui-test-123'
    })
    vi.mocked(testService.connectToTestStream).mockImplementation((id, onMessage, onError, onClose) => {
      streamCallbacks.onMessage = onMessage
      streamCallbacks.onError = onError
      streamCallbacks.onClose = onClose
      return () => {} // cleanup function
    })
    vi.mocked(testService.cancelTestExecution).mockResolvedValue(undefined)
    vi.mocked(testService.disconnectAllStreams).mockReturnValue(undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Display', () => {
    it('should show test execution status', () => {
      render(<TestStatus />)

      // Should show both test sections
      expect(screen.getByText('Python Tests')).toBeInTheDocument()
      expect(screen.getByText('React UI Tests')).toBeInTheDocument()

      // Should show ready status initially
      const readyStatuses = screen.getAllByText('Ready')
      expect(readyStatuses).toHaveLength(2)

      // Should show initial logs
      expect(screen.getByText('> Ready to run Python tests...')).toBeInTheDocument()
      expect(screen.getByText('> Ready to run React UI tests...')).toBeInTheDocument()
    })

    it('should toggle between pretty and raw display modes', async () => {
      const user = userEvent.setup()
      render(<TestStatus />)

      // Should default to pretty mode
      expect(screen.getByText('Pretty')).toHaveClass('bg-cyan-100')
      expect(screen.getByText('Raw')).not.toHaveClass('bg-cyan-100')

      // Toggle to raw mode
      await user.click(screen.getByText('Raw'))

      expect(screen.getByText('Raw')).toHaveClass('bg-cyan-100')
      expect(screen.getByText('Pretty')).not.toHaveClass('bg-cyan-100')
    })
  })

  describe('Test Execution', () => {
    it('should run backend tests', async () => {
      const user = userEvent.setup()
      render(<TestStatus />)

      // Find Python test section
      const pythonSection = screen.getByText('Python Tests').closest('.bg-gray-900')
      const runButton = within(pythonSection!).getByTitle('Run tests')

      await user.click(runButton)

      expect(testService.runMCPTests).toHaveBeenCalled()
      
      // Should update UI to show running state
      await waitFor(() => {
        expect(within(pythonSection!).getByText('Running...')).toBeInTheDocument()
      })

      // Should show execution ID
      expect(screen.getByText('> Execution ID: test-123')).toBeInTheDocument()
    })

    it('should run frontend tests', async () => {
      const user = userEvent.setup()
      render(<TestStatus />)

      // Find React UI test section
      const uiSection = screen.getByText('React UI Tests').closest('.bg-gray-900')
      const runButton = within(uiSection!).getByTitle('Run tests')

      await user.click(runButton)

      expect(testService.runUITestsWithStreaming).toHaveBeenCalled()
      
      // Should update UI to show running state
      await waitFor(() => {
        expect(within(uiSection!).getByText('Running...')).toBeInTheDocument()
      })

      // Should show execution ID
      expect(screen.getByText('> Execution ID: ui-test-123')).toBeInTheDocument()
    })

    it('should cancel running tests', async () => {
      const user = userEvent.setup()
      render(<TestStatus />)

      // Start Python tests
      const pythonSection = screen.getByText('Python Tests').closest('.bg-gray-900')
      const runButton = within(pythonSection!).getByTitle('Run tests')
      await user.click(runButton)

      // Wait for running state
      await waitFor(() => {
        expect(within(pythonSection!).getByText('Running...')).toBeInTheDocument()
      })

      // Cancel button should now be visible
      const cancelButton = within(pythonSection!).getByTitle('Cancel test')
      await user.click(cancelButton)

      expect(testService.cancelTestExecution).toHaveBeenCalledWith('test-123')

      // Simulate cancellation message
      if (streamCallbacks.onMessage) {
        streamCallbacks.onMessage({
          type: 'cancelled',
          message: 'Test execution cancelled'
        })
      }

      await waitFor(() => {
        expect(within(pythonSection!).getByText('Cancelled')).toBeInTheDocument()
      })
    })
  })

  describe('Test Output', () => {
    it('should display test output', async () => {
      const user = userEvent.setup()
      render(<TestStatus />)

      // Start Python tests
      const pythonSection = screen.getByText('Python Tests').closest('.bg-gray-900')
      const runButton = within(pythonSection!).getByTitle('Run tests')
      await user.click(runButton)

      // Simulate test output messages
      if (streamCallbacks.onMessage) {
        streamCallbacks.onMessage({
          type: 'output',
          message: 'test_basic.py::test_example PASSED [0.5s]'
        })
        streamCallbacks.onMessage({
          type: 'output',
          message: 'test_auth.py::test_login FAILED [1.2s]'
        })
      }

      // Check raw output
      await user.click(screen.getByText('Raw'))
      expect(screen.getByText('test_basic.py::test_example PASSED [0.5s]')).toBeInTheDocument()
      expect(screen.getByText('test_auth.py::test_login FAILED [1.2s]')).toBeInTheDocument()

      // Check pretty output
      await user.click(screen.getByText('Pretty'))
      
      // Should show test results with icons
      expect(screen.getByText('test_example')).toBeInTheDocument()
      expect(screen.getByText('test_login')).toBeInTheDocument()
      
      // Should show duration
      expect(screen.getByText('0.50s')).toBeInTheDocument()
      expect(screen.getByText('1.20s')).toBeInTheDocument()
    })

    it('should show test summary', async () => {
      const user = userEvent.setup()
      render(<TestStatus />)

      // Start Python tests
      const pythonSection = screen.getByText('Python Tests').closest('.bg-gray-900')
      const runButton = within(pythonSection!).getByTitle('Run tests')
      await user.click(runButton)

      // Simulate test completion with summary
      if (streamCallbacks.onMessage) {
        streamCallbacks.onMessage({
          type: 'output',
          message: '10 failed | 37 passed (47)'
        })
        streamCallbacks.onMessage({
          type: 'completed',
          data: {
            duration: 15.5,
            exit_code: 0
          }
        })
      }

      await waitFor(() => {
        // Check summary in pretty mode
        const summary = within(pythonSection!).getByText('Total:').parentElement
        expect(within(summary!).getByText('47')).toBeInTheDocument()
        expect(within(summary!).getByText('37')).toBeInTheDocument()
        expect(within(summary!).getByText('10')).toBeInTheDocument()
      })

      // Should show passed status
      expect(within(pythonSection!).getByText('Passed')).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('should handle test failures', async () => {
      const user = userEvent.setup()
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })

      render(<TestStatus />)

      // Start Python tests
      const pythonSection = screen.getByText('Python Tests').closest('.bg-gray-900')
      const runButton = within(pythonSection!).getByTitle('Run tests')
      await user.click(runButton)

      // Simulate error
      if (streamCallbacks.onMessage) {
        streamCallbacks.onMessage({
          type: 'error',
          message: 'Test execution failed: Connection timeout'
        })
      }

      await waitFor(() => {
        expect(screen.getByText('> Error: Test execution failed: Connection timeout')).toBeInTheDocument()
        expect(within(pythonSection!).getByText('Failed')).toBeInTheDocument()
      })

      // In pretty mode, should show errors section
      await user.click(screen.getByText('Pretty'))
      
      const errorSection = within(pythonSection!).getByText(/Errors/)
      expect(errorSection).toBeInTheDocument()
      
      // Should be able to expand errors
      await user.click(errorSection)
      expect(screen.getByText('Test execution failed: Connection timeout')).toBeInTheDocument()
    })

    it('should handle WebSocket connection errors', async () => {
      const user = userEvent.setup()
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })

      render(<TestStatus />)

      // Start tests
      const pythonSection = screen.getByText('Python Tests').closest('.bg-gray-900')
      await user.click(within(pythonSection!).getByTitle('Run tests'))

      // Simulate WebSocket error
      if (streamCallbacks.onError) {
        streamCallbacks.onError(new Error('WebSocket connection failed'))
      }

      await waitFor(() => {
        expect(showToast).toHaveBeenCalledWith('WebSocket connection error', 'error')
        expect(screen.getByText('> WebSocket connection error')).toBeInTheDocument()
      })
    })
  })

  describe('Cleanup', () => {
    it('should cleanup WebSocket connections on unmount', () => {
      const { unmount } = render(<TestStatus />)

      unmount()

      expect(testService.disconnectAllStreams).toHaveBeenCalled()
    })
  })
})