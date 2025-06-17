import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import { agentChatService } from '@/services/agentChatService'
import { MockWebSocket } from '../setup'

// Mock fetch globally
(globalThis as any).fetch = vi.fn()

interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  agent_type?: string;
}

interface WebSocketMessage {
  type: 'message' | 'typing' | 'ping' | 'stream_chunk' | 'stream_complete' | 'connection_confirmed' | 'heartbeat' | 'pong';
  data?: any;
  content?: string;
  session_id?: string;
  is_typing?: boolean;
}

describe('agentChatService', () => {
  let mockFetch: ReturnType<typeof vi.fn>
  let activeWebSockets: MockWebSocket[] = []

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch = vi.mocked((globalThis as any).fetch)
    activeWebSockets = []
    
    // Track created WebSockets
    const OriginalMockWebSocket = MockWebSocket
    ;(globalThis as any).WebSocket = class extends OriginalMockWebSocket {
      constructor(url: string) {
        super(url)
        activeWebSockets.push(this)
      }
    }
  })

  afterEach(() => {
    // Close all active WebSockets
    activeWebSockets.forEach(ws => {
      if (ws.readyState === MockWebSocket.OPEN) {
        ws.close()
      }
    })
    vi.restoreAllMocks()
  })

  describe('Session Management', () => {
    it('should create a new chat session with agent', async () => {
      const mockSessionId = 'session-123'
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: mockSessionId })
      })

      const result = await agentChatService.createSession('project-123', 'docs')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/agent-chat/sessions'),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: 'project-123',
            agent_type: 'docs'
          })
        }
      )
      expect(result.session_id).toBe(mockSessionId)
    })

    it('should retrieve session details with messages', async () => {
      const mockSession = {
        session_id: 'session-123',
        project_id: 'project-123',
        messages: [
          {
            id: 'msg-1',
            content: 'Hello',
            sender: 'user',
            timestamp: '2024-01-01T00:00:00Z'
          }
        ],
        agent_type: 'docs',
        created_at: '2024-01-01T00:00:00Z'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session: mockSession })
      })

      const session = await agentChatService.getSession('session-123')

      expect(session.messages[0].timestamp).toBeInstanceOf(Date)
      expect(session.created_at).toBeInstanceOf(Date)
    })

    test.each([
      { status: 400, statusText: 'Bad Request' },
      { status: 404, statusText: 'Not Found' },
      { status: 500, statusText: 'Internal Server Error' }
    ])('should handle $status errors when creating session', async ({ status, statusText }: { status: number, statusText: string }) => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status,
        statusText
      })

      await expect(agentChatService.createSession()).rejects.toThrow(
        `Failed to create chat session: ${statusText}`
      )
    })
  })

  describe('WebSocket Communication', () => {
    it('should establish WebSocket connection and handle messages', async () => {
      const sessionId = 'session-123'
      const onMessage = vi.fn()
      const onTyping = vi.fn()

      agentChatService.connectWebSocket(sessionId, onMessage, onTyping)

      // Wait for WebSocket to be created
      await vi.waitFor(() => expect(activeWebSockets.length).toBe(1))
      
      const ws = activeWebSockets[0]
      
      // Simulate connection opening
      ws.readyState = MockWebSocket.OPEN
      ws.onopen?.(new Event('open'))

      // Test message handling
      const chatMessage: ChatMessage = {
        id: 'msg-1',
        content: 'Hello from agent',
        sender: 'agent',
        timestamp: new Date()
      }

      const wsMessage: WebSocketMessage = {
        type: 'message',
        data: chatMessage
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(wsMessage)
      }))

      expect(onMessage).toHaveBeenCalledWith(chatMessage)
    })

    it('should handle streaming responses with chunks', async () => {
      const sessionId = 'session-123'
      const onMessage = vi.fn()
      const onTyping = vi.fn()
      const onStreamChunk = vi.fn()
      const onStreamComplete = vi.fn()

      agentChatService.connectWebSocket(
        sessionId, 
        onMessage, 
        onTyping,
        onStreamChunk,
        onStreamComplete
      )

      await vi.waitFor(() => expect(activeWebSockets.length).toBe(1))
      const ws = activeWebSockets[0]
      ws.readyState = MockWebSocket.OPEN

      // Send stream chunks
      const chunks = ['Hello', ' from', ' streaming', ' agent']
      
      for (const chunk of chunks) {
        ws.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify({
            type: 'stream_chunk',
            content: chunk
          })
        }))
      }

      // Send stream complete
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({ type: 'stream_complete' })
      }))

      expect(onStreamChunk).toHaveBeenCalledTimes(chunks.length)
      chunks.forEach((chunk, index) => {
        expect(onStreamChunk).toHaveBeenNthCalledWith(index + 1, chunk)
      })
      expect(onStreamComplete).toHaveBeenCalledOnce()
    })

    it('should handle typing indicators', async () => {
      const sessionId = 'session-123'
      const onMessage = vi.fn()
      const onTyping = vi.fn()

      agentChatService.connectWebSocket(sessionId, onMessage, onTyping)

      await vi.waitFor(() => expect(activeWebSockets.length).toBe(1))
      const ws = activeWebSockets[0]
      ws.readyState = MockWebSocket.OPEN

      // Test typing start
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'typing',
          is_typing: true
        })
      }))

      expect(onTyping).toHaveBeenCalledWith(true)

      // Test typing stop
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'typing',
          is_typing: false
        })
      }))

      expect(onTyping).toHaveBeenCalledWith(false)
    })

    it('should handle heartbeat/pong mechanism', async () => {
      const sessionId = 'session-123'
      const onMessage = vi.fn()
      const onTyping = vi.fn()

      agentChatService.connectWebSocket(sessionId, onMessage, onTyping)

      await vi.waitFor(() => expect(activeWebSockets.length).toBe(1))
      const ws = activeWebSockets[0]
      ws.readyState = MockWebSocket.OPEN

      // Simulate heartbeat from server
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'heartbeat',
          session_id: sessionId
        })
      }))

      // Should respond with ping
      expect(ws.send).toHaveBeenCalledWith('ping')
    })
  })

  describe('Message Sending', () => {
    it('should send messages via REST API', async () => {
      const sessionId = 'session-123'
      const message = 'Hello agent'
      const context = { project_id: 'project-123' }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      })

      await agentChatService.sendMessage(sessionId, message, context)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/agent-chat/sessions/${sessionId}/messages`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, context })
        }
      )
    })

    it('should handle send message errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Rate Limited'
      })

      await expect(
        agentChatService.sendMessage('session-123', 'Hello')
      ).rejects.toThrow('Failed to send message: Rate Limited')
    })
  })

  describe('Reconnection Logic', () => {
    it('should attempt reconnection on unexpected disconnect', async () => {
      const sessionId = 'session-123'
      const onMessage = vi.fn()
      const onTyping = vi.fn()
      const onClose = vi.fn()

      // Mock server status check
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'online' })
      })

      agentChatService.connectWebSocket(sessionId, onMessage, onTyping, undefined, undefined, undefined, onClose)

      await vi.waitFor(() => expect(activeWebSockets.length).toBe(1))
      const ws = activeWebSockets[0]
      ws.readyState = MockWebSocket.OPEN

      // Simulate abnormal closure
      ws.readyState = MockWebSocket.CLOSED
      ws.onclose?.(new CloseEvent('close', { code: 1006, reason: 'Connection lost' }))

      expect(onClose).toHaveBeenCalled()

      // Wait for reconnection attempt
      await vi.waitFor(() => expect(activeWebSockets.length).toBe(2), { timeout: 2000 })
      
      const newWs = activeWebSockets[1]
      expect(newWs.url).toContain(sessionId)
    })

    it('should stop reconnection after max attempts', async () => {
      const sessionId = 'session-123'
      const onMessage = vi.fn()
      const onTyping = vi.fn()

      // Mock server status check to always return online
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'online' })
      })

      agentChatService.connectWebSocket(sessionId, onMessage, onTyping)

      // Simulate multiple disconnections
      for (let i = 0; i < 5; i++) {
        await vi.waitFor(() => expect(activeWebSockets.length).toBeGreaterThan(i))
        const ws = activeWebSockets[i]
        ws.readyState = MockWebSocket.CLOSED
        ws.onclose?.(new CloseEvent('close', { code: 1006 }))
        
        // Allow time for reconnection
        await new Promise(resolve => setTimeout(resolve, 100))
      }

      // After max attempts (3), should not create more connections
      await new Promise(resolve => setTimeout(resolve, 500))
      expect(activeWebSockets.length).toBeLessThanOrEqual(4) // Initial + 3 reconnects
    })

    it('should handle session invalidation (404/403)', async () => {
      const sessionId = 'session-123'
      const onMessage = vi.fn()
      const onTyping = vi.fn()

      agentChatService.connectWebSocket(sessionId, onMessage, onTyping)

      await vi.waitFor(() => expect(activeWebSockets.length).toBe(1))
      const ws = activeWebSockets[0]

      // Mock session verification to return 404
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404
      })

      // Simulate WebSocket error and immediate close
      ws.readyState = MockWebSocket.CLOSED
      ws.onerror?.(new Event('error'))

      // Should attempt to verify session
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/agent-chat/sessions/${sessionId}`)
      ))
    })
  })

  describe('Connection State Management', () => {
    it('should track connection state accurately', () => {
      const sessionId = 'session-123'
      
      expect(agentChatService.isConnected(sessionId)).toBe(false)
      
      agentChatService.connectWebSocket(sessionId, vi.fn(), vi.fn())
      
      // After connection attempt, should have a WebSocket
      expect(agentChatService.getConnectionState(sessionId)).toBe(MockWebSocket.CONNECTING)
    })

    it('should clean up resources on disconnect', async () => {
      const sessionId = 'session-123'
      const onMessage = vi.fn()
      const onTyping = vi.fn()

      agentChatService.connectWebSocket(sessionId, onMessage, onTyping)
      
      await vi.waitFor(() => expect(activeWebSockets.length).toBe(1))
      
      agentChatService.disconnectWebSocket(sessionId)
      
      expect(agentChatService.isConnected(sessionId)).toBe(false)
      expect(agentChatService.getConnectionState(sessionId)).toBe(null)
    })

    it('should disconnect all sessions', async () => {
      // Create multiple sessions
      const sessions = ['session-1', 'session-2', 'session-3']
      
      sessions.forEach(sessionId => {
        agentChatService.connectWebSocket(sessionId, vi.fn(), vi.fn())
      })

      await vi.waitFor(() => expect(activeWebSockets.length).toBe(3))
      
      agentChatService.disconnectAll()
      
      sessions.forEach(sessionId => {
        expect(agentChatService.isConnected(sessionId)).toBe(false)
      })
    })
  })

  describe('Server Status Monitoring', () => {
    it('should check server status and notify handlers', async () => {
      const sessionId = 'session-123'
      const statusHandler = vi.fn()

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'online' })
      })

      agentChatService.onStatusChange(sessionId, statusHandler)
      
      // Trigger a server status check by attempting connection
      agentChatService.connectWebSocket(sessionId, vi.fn(), vi.fn())
      
      // Simulate connection failure
      await vi.waitFor(() => expect(activeWebSockets.length).toBe(1))
      const ws = activeWebSockets[0]
      ws.readyState = MockWebSocket.CLOSED
      ws.onclose?.(new CloseEvent('close', { code: 1006 }))

      // Should check server status
      await vi.waitFor(() => expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/agent-chat/status'),
        expect.any(Object)
      ))

      // Status handler should be called
      await vi.waitFor(() => expect(statusHandler).toHaveBeenCalled())
    })
  })

  describe('Error Handling', () => {
    test.each([
      { 
        scenario: 'network error',
        error: new Event('error'),
        expectedBehavior: 'should trigger error handler'
      },
      {
        scenario: 'invalid JSON message',
        message: 'invalid json',
        expectedBehavior: 'should not crash'
      },
      {
        scenario: 'unknown message type',
        message: JSON.stringify({ type: 'unknown_type' }),
        expectedBehavior: 'should log warning'
      }
    ])('should handle $scenario gracefully', async ({ error, message }: { error?: Event, message?: string }) => {
      const sessionId = 'session-123'
      const onMessage = vi.fn()
      const onTyping = vi.fn()
      const onError = vi.fn()
      const consoleWarn = vi.spyOn(console, 'warn').mockImplementation()
      const consoleError = vi.spyOn(console, 'error').mockImplementation()

      agentChatService.connectWebSocket(sessionId, onMessage, onTyping, undefined, undefined, onError)

      await vi.waitFor(() => expect(activeWebSockets.length).toBe(1))
      const ws = activeWebSockets[0]

      if (error) {
        ws.onerror?.(error)
        expect(onError).toHaveBeenCalledWith(error)
      } else if (message) {
        ws.onmessage?.(new MessageEvent('message', { data: message }))
        
        if (message === 'invalid json') {
          expect(consoleError).toHaveBeenCalled()
        } else {
          expect(consoleWarn).toHaveBeenCalled()
        }
      }

      consoleWarn.mockRestore()
      consoleError.mockRestore()
    })
  })
})