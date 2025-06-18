import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ArchonChatPanel } from '@/components/layouts/ArchonChatPanel'
import { agentChatService } from '@/services/agentChatService'
import type { ChatMessage } from '@/services/agentChatService'

// Mock dependencies
vi.mock('@/services/agentChatService')

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  Send: ({ className }: any) => <span className={className} data-testid="send-icon">Send</span>,
  User: ({ className }: any) => <span className={className} data-testid="user-icon">User</span>,
  WifiOff: ({ className }: any) => <span className={className} data-testid="wifi-off-icon">WifiOff</span>,
  RefreshCw: ({ className }: any) => <span className={className} data-testid="refresh-icon">RefreshCw</span>
}))

// Mock animations
vi.mock('@/components/animations/Animations', () => ({
  ArchonLoadingSpinner: ({ size }: any) => <div data-testid="loading-spinner" data-size={size}>Loading...</div>,
  EdgeLitEffect: ({ color }: any) => <div data-testid="edge-lit-effect" data-color={color} />
}))

describe('ArchonChatPanel', () => {
  const mockSessionId = 'test-session-123'
  const mockMessages: ChatMessage[] = [
    {
      id: 'msg-1',
      content: 'Hello! How can I help you?',
      sender: 'agent',
      timestamp: new Date('2024-01-01T10:00:00'),
      agent_type: 'rag'
    },
    {
      id: 'msg-2',
      content: 'Tell me about the documentation',
      sender: 'user',
      timestamp: new Date('2024-01-01T10:01:00')
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    // Default mock implementations
    vi.mocked(agentChatService.createSession).mockResolvedValue({ session_id: mockSessionId })
    vi.mocked(agentChatService.getSession).mockResolvedValue({
      session_id: mockSessionId,
      agent_type: 'rag',
      messages: mockMessages,
      created_at: new Date()
    })
    vi.mocked(agentChatService.connectWebSocket).mockResolvedValue()
    vi.mocked(agentChatService.sendMessage).mockResolvedValue({} as any)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Initialization', () => {
    it('should initialize chat session on mount', async () => {
      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(agentChatService.createSession).toHaveBeenCalled()
        expect(agentChatService.getSession).toHaveBeenCalledWith(mockSessionId)
        expect(agentChatService.connectWebSocket).toHaveBeenCalled()
      })
    })

    it('should display initial messages', async () => {
      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(screen.getByText('Hello! How can I help you?')).toBeInTheDocument()
        expect(screen.getByText('Tell me about the documentation')).toBeInTheDocument()
      })
    })

    it('should show connection status', async () => {
      render(<ArchonChatPanel />)

      // Initially connecting
      expect(screen.getByText('Connecting...')).toBeInTheDocument()

      // Simulate connection established
      const onStatusChange = vi.mocked(agentChatService.onStatusChange).mock.calls[0]?.[1]
      onStatusChange?.('online')

      await waitFor(() => {
        expect(screen.getByText('Online')).toBeInTheDocument()
      })
    })

    it('should handle WebSocket disabled by environment', async () => {
      // Mock environment variable
      vi.stubEnv('VITE_ENABLE_WEBSOCKET', 'false')

      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(screen.getByText('Agent chat is currently disabled')).toBeInTheDocument()
      })

      vi.unstubAllEnvs()
    })
  })

  describe('Message Sending', () => {
    it('should send chat messages to knowledge base', async () => {
      const user = userEvent.setup()
      render(<ArchonChatPanel />)

      // Wait for initialization
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask about documentation...')).toBeInTheDocument()
      })

      // Simulate connection online
      const onStatusChange = vi.mocked(agentChatService.onStatusChange).mock.calls[0]?.[1]
      onStatusChange?.('online')

      const input = screen.getByPlaceholderText('Ask about documentation...')
      const sendButton = screen.getByRole('button')

      // Type and send message
      await user.type(input, 'What is Archon?')
      await user.click(sendButton)

      expect(agentChatService.sendMessage).toHaveBeenCalledWith(mockSessionId, 'What is Archon?')
      expect(input).toHaveValue('')
    })

    it('should send message on Enter key', async () => {
      const user = userEvent.setup()
      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask about documentation...')).toBeInTheDocument()
      })

      // Simulate connection online
      const onStatusChange = vi.mocked(agentChatService.onStatusChange).mock.calls[0]?.[1]
      onStatusChange?.('online')

      const input = screen.getByPlaceholderText('Ask about documentation...')

      await user.type(input, 'Test message{Enter}')

      expect(agentChatService.sendMessage).toHaveBeenCalledWith(mockSessionId, 'Test message')
    })

    it('should not send empty messages', async () => {
      const user = userEvent.setup()
      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask about documentation...')).toBeInTheDocument()
      })

      // Simulate connection online
      const onStatusChange = vi.mocked(agentChatService.onStatusChange).mock.calls[0]?.[1]
      onStatusChange?.('online')

      const sendButton = screen.getByRole('button')
      
      await user.click(sendButton)

      expect(agentChatService.sendMessage).not.toHaveBeenCalled()
    })

    it('should disable send when offline', async () => {
      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask about documentation...')).toBeInTheDocument()
      })

      // Simulate offline status
      const onStatusChange = vi.mocked(agentChatService.onStatusChange).mock.calls[0]?.[1]
      onStatusChange?.('offline')

      const input = screen.getByPlaceholderText('Chat is offline...')
      const sendButton = screen.getByRole('button')

      expect(input).toBeDisabled()
      expect(sendButton).toBeDisabled()
    })
  })

  describe('Real-time Updates', () => {
    it('should display incoming messages', async () => {
      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(agentChatService.connectWebSocket).toHaveBeenCalled()
      })

      // Get the message callback
      const onMessage = vi.mocked(agentChatService.connectWebSocket).mock.calls[0]?.[1]

      // Simulate incoming message
      const newMessage: ChatMessage = {
        id: 'msg-3',
        content: 'Here is the documentation information...',
        sender: 'agent',
        timestamp: new Date()
      }

      onMessage?.(newMessage)

      await waitFor(() => {
        expect(screen.getByText('Here is the documentation information...')).toBeInTheDocument()
      })
    })

    it('should show typing indicator', async () => {
      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(agentChatService.connectWebSocket).toHaveBeenCalled()
      })

      // Get the typing callback
      const onTyping = vi.mocked(agentChatService.connectWebSocket).mock.calls[0]?.[2]

      // Simulate typing
      onTyping?.(true)

      await waitFor(() => {
        expect(screen.getByText('Agent is typing...')).toBeInTheDocument()
        expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
      })

      // Stop typing
      onTyping?.(false)

      await waitFor(() => {
        expect(screen.queryByText('Agent is typing...')).not.toBeInTheDocument()
      })
    })

    it('should handle streaming messages', async () => {
      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(agentChatService.connectWebSocket).toHaveBeenCalled()
      })

      // Get the streaming callbacks
      const onStreamChunk = vi.mocked(agentChatService.connectWebSocket).mock.calls[0]?.[3]
      const onStreamComplete = vi.mocked(agentChatService.connectWebSocket).mock.calls[0]?.[4]

      // Simulate streaming
      onStreamChunk?.('This is ')
      onStreamChunk?.('a streaming ')
      onStreamChunk?.('message.')

      await waitFor(() => {
        expect(screen.getByText('This is a streaming message.')).toBeInTheDocument()
      })

      // Complete stream
      onStreamComplete?.()

      // Verify streaming indicator is removed
      await waitFor(() => {
        const messages = screen.getAllByText(/This is a streaming message/)
        expect(messages).toHaveLength(0) // Should be cleared after completion
      })
    })
  })

  describe('Connection Management', () => {
    it('should handle connection errors', async () => {
      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(agentChatService.connectWebSocket).toHaveBeenCalled()
      })

      // Get the error callback
      const onError = vi.mocked(agentChatService.connectWebSocket).mock.calls[0]?.[5]

      // Simulate error
      onError?.(new Event('error'))

      // Status change should handle the error display
      const onStatusChange = vi.mocked(agentChatService.onStatusChange).mock.calls[0]?.[1]
      onStatusChange?.('offline')

      await waitFor(() => {
        expect(screen.getByText('Chat Offline')).toBeInTheDocument()
      })
    })

    it('should show offline warning in input area', async () => {
      render(<ArchonChatPanel />)

      // Simulate offline status
      const onStatusChange = vi.mocked(agentChatService.onStatusChange).mock.calls[0]?.[1]
      onStatusChange?.('offline')

      await waitFor(() => {
        expect(screen.getByText(/Chat is currently offline/)).toBeInTheDocument()
      })
    })

    it('should handle manual reconnection', async () => {
      vi.mocked(agentChatService.manualReconnect).mockResolvedValue(true)
      const user = userEvent.setup()
      
      render(<ArchonChatPanel />)

      // Simulate offline status
      const onStatusChange = vi.mocked(agentChatService.onStatusChange).mock.calls[0]?.[1]
      onStatusChange?.('offline')

      await waitFor(() => {
        expect(screen.getByText('Reconnect')).toBeInTheDocument()
      })

      const reconnectButton = screen.getByText('Reconnect').closest('button') as HTMLButtonElement
      await user.click(reconnectButton)

      expect(agentChatService.manualReconnect).toHaveBeenCalledWith(mockSessionId)

      await waitFor(() => {
        expect(screen.getByText('Connecting...')).toBeInTheDocument()
      })
    })

    it('should handle failed reconnection', async () => {
      vi.mocked(agentChatService.manualReconnect).mockResolvedValue(false)
      const user = userEvent.setup()
      
      render(<ArchonChatPanel />)

      // Simulate offline status
      const onStatusChange = vi.mocked(agentChatService.onStatusChange).mock.calls[0]?.[1]
      onStatusChange?.('offline')

      await waitFor(() => {
        expect(screen.getByText('Reconnect')).toBeInTheDocument()
      })

      const reconnectButton = screen.getByText('Reconnect').closest('button') as HTMLButtonElement
      await user.click(reconnectButton)

      await waitFor(() => {
        expect(screen.getByText(/Reconnection failed/)).toBeInTheDocument()
      })
    })
  })

  describe('UI Features', () => {
    it('should render panel header with logo and title', () => {
      render(<ArchonChatPanel />)

      expect(screen.getByAltText('Archon')).toHaveAttribute('src', '/logo-neon.svg')
      expect(screen.getByText('Documentation Assistant')).toBeInTheDocument()
    })

    it('should format message timestamps', async () => {
      render(<ArchonChatPanel />)

      await waitFor(() => {
        // Check for formatted time (10:00 AM format)
        const timeElements = screen.getAllByText(/\d{1,2}:\d{2}/)
        expect(timeElements.length).toBeGreaterThan(0)
      })
    })

    it('should style user and agent messages differently', async () => {
      render(<ArchonChatPanel />)

      await waitFor(() => {
        const agentMessage = screen.getByText('Hello! How can I help you?').closest('div')
        const userMessage = screen.getByText('Tell me about the documentation').closest('div')

        expect(agentMessage).toHaveClass('bg-blue-100/80')
        expect(userMessage).toHaveClass('bg-purple-100/80')
      })
    })

    it('should show appropriate icons for messages', async () => {
      render(<ArchonChatPanel />)

      await waitFor(() => {
        // Agent messages should have Archon logo
        const agentMessage = screen.getByText('Hello! How can I help you?').closest('.rounded-lg')
        expect(agentMessage?.querySelector('img[alt="Archon"]')).toBeInTheDocument()

        // User messages should have user icon
        const userMessage = screen.getByText('Tell me about the documentation').closest('.rounded-lg')
        expect(userMessage?.querySelector('[data-testid="user-icon"]')).toBeInTheDocument()
      })
    })
  })

  describe('Panel Resizing', () => {
    it('should render with default width', () => {
      render(<ArchonChatPanel />)

      const panel = document.querySelector('[data-id]')
      expect(panel).toHaveStyle({ width: '320px' })
    })

    it('should show drag handle', () => {
      render(<ArchonChatPanel />)

      const dragHandle = document.querySelector('.cursor-ew-resize')
      expect(dragHandle).toBeInTheDocument()
      expect(dragHandle).toHaveClass('w-1.5', 'h-full')
    })

    test.skip('should handle panel resizing via drag', async () => {
      // Skipping due to complexity of simulating drag events
      // This would require extensive mouse event simulation
    })
  })

  describe('Error Handling', () => {
    it('should show error when session creation fails', async () => {
      vi.mocked(agentChatService.createSession).mockRejectedValue(new Error('Server error'))

      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(screen.getByText(/Failed to initialize chat/)).toBeInTheDocument()
      })
    })

    it('should show error when message send fails', async () => {
      vi.mocked(agentChatService.sendMessage).mockRejectedValue(new Error('Send failed'))
      const user = userEvent.setup()

      render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask about documentation...')).toBeInTheDocument()
      })

      // Simulate connection online
      const onStatusChange = vi.mocked(agentChatService.onStatusChange).mock.calls[0]?.[1]
      onStatusChange?.('online')

      const input = screen.getByPlaceholderText('Ask about documentation...')
      await user.type(input, 'Test message')
      await user.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByText(/Failed to send message/)).toBeInTheDocument()
      })
    })
  })

  describe('Cleanup', () => {
    it('should disconnect WebSocket on unmount', async () => {
      const { unmount } = render(<ArchonChatPanel />)

      await waitFor(() => {
        expect(agentChatService.createSession).toHaveBeenCalled()
      })

      unmount()

      expect(agentChatService.disconnectWebSocket).toHaveBeenCalledWith(mockSessionId)
      expect(agentChatService.offStatusChange).toHaveBeenCalledWith(mockSessionId)
    })
  })
})