import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import { testService } from '@/services/testService'
import { MockWebSocket } from '../setup'
import type { TestExecution, TestStreamMessage, TestStatus, TestHistory } from '@/services/testService'

// Mocks are already set up in setup.ts

describe('testService', () => {
  let mockFetch: ReturnType<typeof vi.fn>
  const baseUrl = 'http://localhost:8080'
  
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch = vi.mocked((globalThis as any).fetch)
    // Clear any WebSocket connections
    testService.disconnectAllStreams()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    testService.disconnectAllStreams()
  })

  describe('Python Test Execution', () => {
    it('should run Python backend tests', async () => {
      const mockExecution: TestExecution = {
        execution_id: 'exec-123',
        test_type: 'mcp',
        status: 'running',
        start_time: '2024-01-01T00:00:00Z'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockExecution
      })

      const result = await testService.runMCPTests()

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/tests/mcp/run`,
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            test_type: 'mcp',
            options: {}
          })
        })
      )
      expect(result).toEqual(mockExecution)
    })

    it('should handle Python test errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Test runner not available' })
      })

      await expect(testService.runMCPTests()).rejects.toThrow('HTTP error! status: 500')
    })
  })

  describe('Frontend Test Execution', () => {
    it('should run frontend Vitest tests', async () => {
      const result = await testService.runUITests()

      expect(result).toMatchObject({
        execution_id: 'test-uuid-123',
        test_type: 'ui',
        status: 'pending',
        start_time: expect.any(String)
      })
    })

    it('should stream UI test output', async () => {
      const onMessage = vi.fn()
      const onError = vi.fn()
      const onComplete = vi.fn()

      // Mock SSE response with chunks
      const encoder = new TextEncoder()
      const stream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('data: {"type":"status","data":{"status":"running"},"message":"Starting tests..."}\n'))
          controller.enqueue(encoder.encode('data: {"type":"output","message":"✓ Test 1 passed"}\n'))
          controller.enqueue(encoder.encode('data: {"type":"output","message":"✗ Test 2 failed"}\n'))
          controller.enqueue(encoder.encode('data: {"type":"completed","data":{"passed":1,"failed":1}}\n'))
          controller.close()
        }
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: stream
      })

      const executionId = await testService.runUITestsWithStreaming(onMessage, onError, onComplete)

      expect(executionId).toBe('test-uuid-123')
      expect(mockFetch).toHaveBeenCalledWith('/api/run-tests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      // Wait for stream processing
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(onMessage).toHaveBeenCalledTimes(5) // Initial status + 4 stream messages
      expect(onMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'output',
          execution_id: 'test-uuid-123',
          message: '✓ Test 1 passed'
        })
      )
      expect(onComplete).toHaveBeenCalled()
    })

    it('should handle streaming errors', async () => {
      const onMessage = vi.fn()
      const onError = vi.fn()

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found'
      })

      await testService.runUITestsWithStreaming(onMessage, onError)

      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Failed to start tests: 404 Not Found'
        })
      )
      expect(onMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'error',
          message: 'Failed to start tests: 404 Not Found'
        })
      )
    })
  })

  describe('WebSocket Test Streaming', () => {
    it('should stream test output through WebSocket', () => {
      const executionId = 'exec-123'
      const onMessage = vi.fn()
      const onError = vi.fn()
      const onClose = vi.fn()

      const cleanup = testService.connectToTestStream(executionId, onMessage, onError, onClose)

      // Get created WebSocket
      const ws = (MockWebSocket as any).instances[0]
      expect(ws.url).toBe(`ws://localhost:8080/api/tests/stream/${executionId}`)

      // Simulate messages
      const message: TestStreamMessage = {
        type: 'output',
        execution_id: executionId,
        message: 'Running test suite...',
        timestamp: '2024-01-01T00:00:00Z'
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify(message)
      }))

      expect(onMessage).toHaveBeenCalledWith(message)
      expect(testService.isStreamConnected(executionId)).toBe(true)

      // Test cleanup
      cleanup()
      expect(ws.close).toHaveBeenCalled()
    })

    it('should handle WebSocket errors gracefully', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation()
      const onMessage = vi.fn()
      const onError = vi.fn()

      testService.connectToTestStream('exec-123', onMessage, onError)
      const ws = (MockWebSocket as any).instances[0]

      // Simulate error
      const error = new Event('error')
      ws.onerror?.(error)

      expect(consoleError).toHaveBeenCalled()
      expect(onError).toHaveBeenCalledWith(error)

      consoleError.mockRestore()
    })

    it('should handle malformed WebSocket messages', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation()
      const onMessage = vi.fn()

      testService.connectToTestStream('exec-123', onMessage)
      const ws = (MockWebSocket as any).instances[0]

      // Send malformed JSON
      ws.onmessage?.(new MessageEvent('message', {
        data: 'invalid json'
      }))

      expect(consoleError).toHaveBeenCalledWith(
        'Failed to parse WebSocket message:',
        expect.any(Error),
        'invalid json'
      )
      expect(onMessage).not.toHaveBeenCalled()

      consoleError.mockRestore()
    })
  })

  describe('Test Status and History', () => {
    it('should get test execution status', async () => {
      const mockStatus: TestStatus = {
        execution_id: 'exec-123',
        status: 'completed',
        start_time: '2024-01-01T00:00:00Z',
        end_time: '2024-01-01T00:05:00Z',
        duration: 300,
        exit_code: 0
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus
      })

      const status = await testService.getTestStatus('exec-123')

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/tests/status/exec-123`,
        expect.any(Object)
      )
      expect(status).toEqual(mockStatus)
    })

    it('should get test execution history', async () => {
      const mockHistory: TestHistory = {
        executions: [
          {
            execution_id: 'exec-1',
            test_type: 'mcp',
            status: 'completed',
            start_time: '2024-01-01T00:00:00Z',
            duration: 120,
            exit_code: 0
          },
          {
            execution_id: 'exec-2',
            test_type: 'ui',
            status: 'failed',
            start_time: '2024-01-01T01:00:00Z',
            duration: 60,
            exit_code: 1
          }
        ],
        total_count: 2
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockHistory
      })

      const history = await testService.getTestHistory()

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/tests/history`,
        expect.any(Object)
      )
      expect(history.executions).toHaveLength(2)
      expect(history.total_count).toBe(2)
    })
  })

  describe('Test Control', () => {
    it('should cancel running tests on request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      })

      await testService.cancelTestExecution('exec-123')

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/tests/execution/exec-123`,
        expect.objectContaining({
          method: 'DELETE'
        })
      )
    })

    it('should handle cancellation errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ error: 'Execution not found' })
      })

      await expect(testService.cancelTestExecution('non-existent')).rejects.toThrow('HTTP error! status: 404')
    })
  })

  describe('Connection Management', () => {
    it('should track multiple WebSocket connections', () => {
      const onMessage = vi.fn()

      // Create multiple connections
      testService.connectToTestStream('exec-1', onMessage)
      testService.connectToTestStream('exec-2', onMessage)
      testService.connectToTestStream('exec-3', onMessage)

      expect(testService.isStreamConnected('exec-1')).toBe(true)
      expect(testService.isStreamConnected('exec-2')).toBe(true)
      expect(testService.isStreamConnected('exec-3')).toBe(true)

      // Disconnect one
      testService.disconnectFromTestStream('exec-2')
      
      expect(testService.isStreamConnected('exec-1')).toBe(true)
      expect(testService.isStreamConnected('exec-2')).toBe(false)
      expect(testService.isStreamConnected('exec-3')).toBe(true)
    })

    it('should disconnect all streams on cleanup', () => {
      const onMessage = vi.fn()

      // Create connections
      testService.connectToTestStream('exec-1', onMessage)
      testService.connectToTestStream('exec-2', onMessage)

      const ws1 = (MockWebSocket as any).instances[0]
      const ws2 = (MockWebSocket as any).instances[1]

      // Disconnect all
      testService.disconnectAllStreams()

      expect(ws1.close).toHaveBeenCalled()
      expect(ws2.close).toHaveBeenCalled()
      expect(testService.isStreamConnected('exec-1')).toBe(false)
      expect(testService.isStreamConnected('exec-2')).toBe(false)
    })

    it('should replace existing connection for same execution ID', () => {
      const onMessage = vi.fn()

      // Create initial connection
      testService.connectToTestStream('exec-123', onMessage)
      const ws1 = (MockWebSocket as any).instances[0]

      // Create new connection with same ID
      testService.connectToTestStream('exec-123', onMessage)
      const ws2 = (MockWebSocket as any).instances[1]

      // Old connection should be closed
      expect(ws1.close).toHaveBeenCalled()
      expect(ws2.close).not.toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    test.each([
      {
        method: 'runMCPTests',
        endpoint: '/api/tests/mcp/run'
      },
      {
        method: 'getTestStatus',
        args: ['exec-123'],
        endpoint: '/api/tests/status/exec-123'
      },
      {
        method: 'getTestHistory',
        endpoint: '/api/tests/history'
      }
    ])('should handle API errors for $method', async ({ method, args = [], endpoint }: { method: string, args?: any[], endpoint: string }) => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ error: 'Internal server error' })
      })

      await expect((testService as any)[method](...args)).rejects.toThrow('Internal server error')
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(testService.runMCPTests()).rejects.toThrow('Failed to call API /api/tests/mcp/run: Network error')
    })

    it('should handle non-Error objects in catch', async () => {
      mockFetch.mockRejectedValueOnce('String error')

      await expect(testService.runMCPTests()).rejects.toThrow('Failed to call API /api/tests/mcp/run: Unknown error')
    })
  })
})