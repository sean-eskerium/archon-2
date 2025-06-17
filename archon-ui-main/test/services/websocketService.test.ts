import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import type { Mock } from 'vitest'
import { MockWebSocket } from '../setup'

// Import after mocking WebSocket is set up in setup.ts
import { WebSocketService, knowledgeWebSocket, crawlWebSocket, taskUpdateWebSocket } from '@/services/websocketService'
import type { TaskUpdateData } from '@/services/websocketService'

describe('WebSocketService', () => {
  let service: WebSocketService
  let mockWebSocket: MockWebSocket

  beforeEach(() => {
    vi.clearAllMocks()
    service = new WebSocketService()
  })

  afterEach(() => {
    service.disconnect()
    vi.restoreAllMocks()
  })

  describe('connection management', () => {
    it('should connect to WebSocket server with correct URL', () => {
      const endpoint = '/api/knowledge/ws'
      service.connect(endpoint)
      
      // Get the created WebSocket instance
      const connections = vi.mocked(MockWebSocket).mock.instances
      expect(connections).toHaveLength(1)
      mockWebSocket = connections[0] as unknown as MockWebSocket
      
      // Verify URL construction
      expect(mockWebSocket.url).toMatch(/ws:\/\/.*:8080\/api\/knowledge\/ws/)
    })

    it('should use wss protocol for https locations', () => {
      Object.defineProperty(window.location, 'protocol', { value: 'https:', writable: true })
      
      const endpoint = '/api/test/ws'
      service.connect(endpoint)
      
      const connections = vi.mocked(MockWebSocket).mock.instances
      mockWebSocket = connections[0] as unknown as MockWebSocket
      
      expect(mockWebSocket.url).toMatch(/wss:\/\//)
    })

    it('should handle automatic reconnection after disconnect', async () => {
      vi.useFakeTimers()
      
      service.connect('/api/test/ws')
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      
      // Simulate connection open
      mockWebSocket.readyState = MockWebSocket.OPEN
      mockWebSocket.onopen?.(new Event('open'))
      
      // Simulate unexpected close
      mockWebSocket.readyState = MockWebSocket.CLOSED
      mockWebSocket.onclose?.(new CloseEvent('close'))
      
      // Advance timers to trigger reconnection
      await vi.advanceTimersByTimeAsync(1000)
      
      // Should create a new WebSocket connection
      expect(vi.mocked(MockWebSocket).mock.instances).toHaveLength(2)
      
      vi.useRealTimers()
    })

    it('should stop reconnecting after max attempts reached', async () => {
      vi.useFakeTimers()
      
      const maxAttempts = 5
      service.connect('/api/test/ws')
      
      // Simulate multiple failed connections
      for (let i = 0; i < maxAttempts + 2; i++) {
        const ws = vi.mocked(MockWebSocket).mock.instances[i] as unknown as MockWebSocket
        ws.onclose?.(new CloseEvent('close'))
        
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s
        if (i < maxAttempts) {
          await vi.advanceTimersByTimeAsync(1000 * Math.pow(2, i))
        }
      }
      
      // Should only create maxAttempts + 1 connections (initial + retries)
      expect(vi.mocked(MockWebSocket).mock.instances).toHaveLength(maxAttempts + 1)
      
      vi.useRealTimers()
    })
  })

  describe('message handling', () => {
    beforeEach(() => {
      service.connect('/api/test/ws')
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      mockWebSocket.readyState = MockWebSocket.OPEN
    })

    test.each([
      { type: 'update', data: { id: 1, name: 'test' } },
      { type: 'delete', data: { id: 2 } },
      { type: 'create', data: { name: 'new' } },
    ])('should handle $type message correctly', ({ type, data }: { type: string; data: any }) => {
      const listener = vi.fn()
      service.addEventListener(type, listener)
      
      // Simulate incoming message
      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify({ type, ...data })
      })
      mockWebSocket.onmessage?.(messageEvent)
      
      expect(listener).toHaveBeenCalledWith({ type, ...data })
    })

    it('should handle malformed JSON messages gracefully', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      const messageEvent = new MessageEvent('message', {
        data: 'invalid json {'
      })
      mockWebSocket.onmessage?.(messageEvent)
      
      expect(consoleError).toHaveBeenCalledWith(
        'Failed to parse WebSocket message:',
        expect.any(Error)
      )
    })

    it('should support multiple listeners for the same message type', () => {
      const listener1 = vi.fn()
      const listener2 = vi.fn()
      const listener3 = vi.fn()
      
      service.addEventListener('update', listener1)
      service.addEventListener('update', listener2)
      service.addEventListener('update', listener3)
      
      const message = { type: 'update', data: 'test' }
      mockWebSocket.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(message)
      }))
      
      expect(listener1).toHaveBeenCalledWith(message)
      expect(listener2).toHaveBeenCalledWith(message)
      expect(listener3).toHaveBeenCalledWith(message)
    })
  })

  describe('event listeners', () => {
    it('should add and remove event listeners correctly', () => {
      const listener1 = vi.fn()
      const listener2 = vi.fn()
      
      service.addEventListener('test', listener1)
      service.addEventListener('test', listener2)
      
      service.connect('/api/test/ws')
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      mockWebSocket.readyState = MockWebSocket.OPEN
      
      // Send message
      const message = { type: 'test', data: 'hello' }
      mockWebSocket.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(message)
      }))
      
      expect(listener1).toHaveBeenCalledWith(message)
      expect(listener2).toHaveBeenCalledWith(message)
      
      // Remove one listener
      service.removeEventListener('test', listener1)
      vi.clearAllMocks()
      
      // Send another message
      mockWebSocket.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(message)
      }))
      
      expect(listener1).not.toHaveBeenCalled()
      expect(listener2).toHaveBeenCalledWith(message)
    })

    it('should handle listener errors without affecting other listeners', () => {
      const errorListener = vi.fn().mockImplementation(() => {
        throw new Error('Listener error')
      })
      const normalListener = vi.fn()
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      service.addEventListener('test', errorListener)
      service.addEventListener('test', normalListener)
      
      service.connect('/api/test/ws')
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      
      const message = { type: 'test', data: 'test' }
      mockWebSocket.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(message)
      }))
      
      expect(errorListener).toHaveBeenCalled()
      expect(normalListener).toHaveBeenCalled()
      expect(consoleError).toHaveBeenCalledWith(
        'Error in WebSocket message listener:',
        expect.any(Error)
      )
    })
  })

  describe('sending messages', () => {
    beforeEach(() => {
      service.connect('/api/test/ws')
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
    })

    it('should send messages when connection is open', () => {
      mockWebSocket.readyState = MockWebSocket.OPEN
      
      const data = { action: 'update', id: 123 }
      service.send(data)
      
      expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify(data))
    })

    test.each([
      MockWebSocket.CONNECTING,
      MockWebSocket.CLOSING,
      MockWebSocket.CLOSED,
    ])('should not send messages when readyState is %s', (readyState: number) => {
      mockWebSocket.readyState = readyState
      
      service.send({ test: 'data' })
      
      expect(mockWebSocket.send).not.toHaveBeenCalled()
    })

    it('should not send messages when WebSocket is null', () => {
      service.disconnect()
      service.send({ test: 'data' })
      
      // Should not throw error
      expect(true).toBe(true)
    })
  })

  describe('disconnect and cleanup', () => {
    it('should close connection and clear listeners on disconnect', () => {
      const listener = vi.fn()
      service.addEventListener('test', listener)
      
      service.connect('/api/test/ws')
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      
      service.disconnect()
      
      expect(mockWebSocket.close).toHaveBeenCalled()
      
      // Verify listeners are cleared
      mockWebSocket.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({ type: 'test' })
      }))
      expect(listener).not.toHaveBeenCalled()
    })
  })

  describe('error handling', () => {
    it('should log WebSocket errors', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      service.connect('/api/test/ws')
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      
      const error = new Event('error')
      mockWebSocket.onerror?.(error)
      
      expect(consoleError).toHaveBeenCalledWith('WebSocket error:', error)
    })
  })
})

describe('TaskUpdateService', () => {
  let mockWebSocket: MockWebSocket
  const projectId = 'test-project-123'

  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(Math, 'random').mockReturnValue(0.123456789)
  })

  afterEach(() => {
    taskUpdateWebSocket.disconnect()
    vi.restoreAllMocks()
  })

  describe('connection with session management', () => {
    it('should generate session ID if not provided', () => {
      const callbacks = { onConnectionEstablished: vi.fn() }
      
      taskUpdateWebSocket.connect(projectId, callbacks)
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      
      expect(mockWebSocket.url).toMatch(/session_id=task-session-/)
    })

    it('should use provided session ID', () => {
      const sessionId = 'custom-session-123'
      const callbacks = { onConnectionEstablished: vi.fn() }
      
      taskUpdateWebSocket.connect(projectId, callbacks, sessionId)
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      
      expect(mockWebSocket.url).toContain(`session_id=${sessionId}`)
    })

    it('should close existing connection before creating new one', () => {
      const callbacks = { onConnectionEstablished: vi.fn() }
      
      // First connection
      taskUpdateWebSocket.connect(projectId, callbacks)
      const firstWs = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      firstWs.readyState = MockWebSocket.OPEN
      
      // Second connection
      taskUpdateWebSocket.connect('another-project', callbacks)
      
      expect(firstWs.close).toHaveBeenCalledWith(1000, 'Client disconnecting')
    })
  })

  describe('message type handling', () => {
    const setupConnection = () => {
      taskUpdateWebSocket.connect(projectId, {})
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[vi.mocked(MockWebSocket).mock.instances.length - 1] as unknown as MockWebSocket
      mockWebSocket.readyState = MockWebSocket.OPEN
    }

    test.each([
      {
        type: 'connection_established',
        callback: 'onConnectionEstablished',
        data: {}
      },
      {
        type: 'initial_tasks',
        callback: 'onInitialTasks',
        data: { tasks: [{ id: 1 }, { id: 2 }] }
      },
      {
        type: 'task_created',
        callback: 'onTaskCreated',
        data: { id: 3, title: 'New Task' }
      },
      {
        type: 'task_updated',
        callback: 'onTaskUpdated',
        data: { id: 1, title: 'Updated Task' }
      },
      {
        type: 'task_deleted',
        callback: 'onTaskDeleted',
        data: { id: 2 }
      },
      {
        type: 'task_archived',
        callback: 'onTaskArchived',
        data: { id: 1 }
      },
      {
        type: 'tasks_updated',
        callback: 'onTasksChange',
        data: { updated_tasks: [{ id: 1 }, { id: 2 }] }
      }
    ])('should handle $type message and call $callback', ({ type, callback, data }: { type: string; callback: string; data: any }) => {
      const callbacks = {
        [callback]: vi.fn()
      }
      
      taskUpdateWebSocket.connect(projectId, callbacks)
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[vi.mocked(MockWebSocket).mock.instances.length - 1] as unknown as MockWebSocket
      
      const message: TaskUpdateData = {
        type: type as any,
        data,
        timestamp: new Date().toISOString(),
        project_id: projectId
      }
      
      mockWebSocket.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(message)
      }))
      
      if (callback === 'onInitialTasks') {
        expect(callbacks[callback]).toHaveBeenCalledWith(data.tasks || [])
      } else if (callback === 'onTasksChange') {
        expect(callbacks[callback]).toHaveBeenCalledWith(data.updated_tasks || [])
      } else if (callback !== 'onConnectionEstablished') {
        expect(callbacks[callback]).toHaveBeenCalledWith(data)
      } else {
        expect(callbacks[callback]).toHaveBeenCalled()
      }
    })

    it('should handle heartbeat and send ping response', () => {
      setupConnection()
      
      const message: TaskUpdateData = {
        type: 'heartbeat',
        data: {},
        timestamp: new Date().toISOString(),
        project_id: projectId
      }
      
      mockWebSocket.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(message)
      }))
      
      expect(mockWebSocket.send).toHaveBeenCalledWith('ping')
    })
  })

  describe('reconnection behavior', () => {
    it('should not reconnect on clean disconnect', () => {
      vi.useFakeTimers()
      
      taskUpdateWebSocket.connect(projectId, {})
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      
      // Simulate clean disconnect
      const closeEvent = new CloseEvent('close', {
        code: 1000,
        reason: 'Client disconnecting'
      })
      mockWebSocket.onclose?.(closeEvent)
      
      vi.advanceTimersByTime(10000)
      
      // Should not create new connections
      expect(vi.mocked(MockWebSocket).mock.instances).toHaveLength(1)
      
      vi.useRealTimers()
    })

    it('should reconnect on unexpected disconnect with max 3 attempts', async () => {
      vi.useFakeTimers()
      
      taskUpdateWebSocket.connect(projectId, {})
      
      // Simulate 4 failed connections (initial + 3 retries)
      for (let i = 0; i < 4; i++) {
        const ws = vi.mocked(MockWebSocket).mock.instances[i] as unknown as MockWebSocket
        ws.onclose?.(new CloseEvent('close', { code: 1006 }))
        
        if (i < 3) {
          await vi.advanceTimersByTimeAsync(5000)
        }
      }
      
      // Should only create 4 connections total
      expect(vi.mocked(MockWebSocket).mock.instances).toHaveLength(4)
      
      vi.useRealTimers()
    })
  })

  describe('connection state', () => {
    it('should report connection state correctly', () => {
      expect(taskUpdateWebSocket.isConnected()).toBe(false)
      
      taskUpdateWebSocket.connect(projectId, {})
      mockWebSocket = vi.mocked(MockWebSocket).mock.instances[0] as unknown as MockWebSocket
      
      mockWebSocket.readyState = MockWebSocket.CONNECTING
      expect(taskUpdateWebSocket.isConnected()).toBe(false)
      
      mockWebSocket.readyState = MockWebSocket.OPEN
      expect(taskUpdateWebSocket.isConnected()).toBe(true)
      
      mockWebSocket.readyState = MockWebSocket.CLOSED
      expect(taskUpdateWebSocket.isConnected()).toBe(false)
    })
  })
})

describe('singleton instances', () => {
  it('should export singleton WebSocket instances', () => {
    expect(knowledgeWebSocket).toBeDefined()
    expect(crawlWebSocket).toBeDefined()
    expect(taskUpdateWebSocket).toBeDefined()
    
    // Verify they are different instances
    expect(knowledgeWebSocket).not.toBe(crawlWebSocket)
    expect(knowledgeWebSocket).not.toBe(taskUpdateWebSocket)
    expect(crawlWebSocket).not.toBe(taskUpdateWebSocket)
  })
})