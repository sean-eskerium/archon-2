import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import { crawlProgressService } from '@/services/crawlProgressService'
import { MockWebSocket } from '../setup'
import type { CrawlProgressData, ProgressStep } from '@/services/crawlProgressService'

// Mock environment
(import.meta as any).env = { VITE_API_URL: 'http://localhost:8080' }

describe('crawlProgressService', () => {
  const wsUrl = 'ws://localhost:8080'
  let consoleLog: ReturnType<typeof vi.spyOn>
  let consoleWarn: ReturnType<typeof vi.spyOn>
  let consoleError: ReturnType<typeof vi.spyOn>
  
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock console methods
    consoleLog = vi.spyOn(console, 'log').mockImplementation()
    consoleWarn = vi.spyOn(console, 'warn').mockImplementation()
    consoleError = vi.spyOn(console, 'error').mockImplementation()
    // Clear any existing connections
    crawlProgressService.disconnect()
    crawlProgressService.isReconnecting = false
  })

  afterEach(() => {
    vi.restoreAllMocks()
    crawlProgressService.disconnect()
    consoleLog.mockRestore()
    consoleWarn.mockRestore()
    consoleError.mockRestore()
  })

  describe('Progress Streaming', () => {
    it('should subscribe to crawl progress updates', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      expect(ws).toBeInstanceOf(MockWebSocket)
      expect(ws.url).toBe(`${wsUrl}/api/crawl-progress/${progressId}`)
      expect(consoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Attempting to connect to WebSocket')
      )
    })

    it('should handle crawl status changes', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      // Simulate connection open
      ws.onopen?.(new Event('open'))
      expect(consoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Connected to crawl progress stream')
      )

      // Test different status messages
      const statusUpdates: CrawlProgressData[] = [
        {
          progressId,
          status: 'starting',
          percentage: 0,
          logs: ['Starting crawl...']
        },
        {
          progressId,
          status: 'crawling',
          percentage: 25,
          currentUrl: 'https://example.com/page1',
          totalPages: 10,
          processedPages: 3,
          logs: ['Crawling page 3 of 10']
        },
        {
          progressId,
          status: 'processing',
          percentage: 75,
          chunksStored: 50,
          wordCount: 5000,
          logs: ['Processing content...']
        },
        {
          progressId,
          status: 'completed',
          percentage: 100,
          duration: '5m 30s',
          logs: ['Crawl completed successfully']
        }
      ]

      statusUpdates.forEach((update, index) => {
        ws.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify({
            type: 'crawl_progress',
            data: update
          })
        }))
        
        expect(onMessage).toHaveBeenNthCalledWith(index + 1, update)
      })

      expect(onMessage).toHaveBeenCalledTimes(statusUpdates.length)
    })

    it('should calculate completion percentage correctly', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      // Test various percentage calculations
      const progressUpdates = [
        { percentage: 0, processedPages: 0, totalPages: 100 },
        { percentage: 25, processedPages: 25, totalPages: 100 },
        { percentage: 50.5, processedPages: 101, totalPages: 200 },
        { percentage: 100, processedPages: 50, totalPages: 50 }
      ]

      progressUpdates.forEach(({ percentage, processedPages, totalPages }) => {
        ws.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify({
            type: 'crawl_progress',
            data: {
              progressId,
              status: 'crawling',
              percentage,
              processedPages,
              totalPages,
              logs: []
            }
          })
        }))
      })

      // Verify all percentages were passed correctly
      progressUpdates.forEach((update, index) => {
        expect(onMessage).toHaveBeenNthCalledWith(
          index + 1,
          expect.objectContaining({ percentage: update.percentage })
        )
      })
    })

    it('should handle multi-step progress tracking', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      const steps: ProgressStep[] = [
        { id: 'fetch', label: 'Fetching content', percentage: 100, status: 'completed' },
        { id: 'parse', label: 'Parsing HTML', percentage: 50, status: 'active' },
        { id: 'extract', label: 'Extracting text', percentage: 0, status: 'pending' },
        { id: 'chunk', label: 'Creating chunks', percentage: 0, status: 'pending' }
      ]

      const progressData: CrawlProgressData = {
        progressId,
        status: 'processing',
        percentage: 37.5, // Average of all steps
        steps,
        currentStep: 'parse',
        stepMessage: 'Parsing document structure...',
        logs: []
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'crawl_progress',
          data: progressData
        })
      }))

      expect(onMessage).toHaveBeenCalledWith(progressData)
      expect(onMessage.mock.calls[0][0].steps).toHaveLength(4)
      expect(onMessage.mock.calls[0][0].currentStep).toBe('parse')
    })

    it('should handle document upload progress', () => {
      const progressId = 'upload-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      const uploadProgress: CrawlProgressData = {
        progressId,
        status: 'extracting',
        percentage: 45,
        uploadType: 'document',
        fileName: 'technical-spec.pdf',
        fileType: 'application/pdf',
        sourceId: 'source-456',
        logs: ['Extracting text from PDF...']
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'crawl_progress',
          data: uploadProgress
        })
      }))

      expect(onMessage).toHaveBeenCalledWith(uploadProgress)
      expect(onMessage.mock.calls[0][0]).toMatchObject({
        uploadType: 'document',
        fileName: 'technical-spec.pdf',
        fileType: 'application/pdf'
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle crawl errors gracefully', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      const errorData: CrawlProgressData = {
        progressId,
        status: 'error',
        percentage: 45,
        error: 'Failed to fetch URL: Connection timeout',
        logs: ['Error occurred during crawl']
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'crawl_error',
          data: errorData
        })
      }))

      expect(onMessage).toHaveBeenCalledWith(errorData)
      expect(onMessage.mock.calls[0][0].error).toBe('Failed to fetch URL: Connection timeout')
    })

    it('should validate progress message format', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      // Test invalid messages
      const invalidMessages = [
        { type: 'crawl_progress', data: null }, // No data
        { type: 'crawl_progress', data: {} }, // No progressId
        { type: 'crawl_progress', data: { progressId, percentage: 'invalid' } }, // Invalid percentage
        { type: 'crawl_progress', data: { progressId, percentage: NaN } } // NaN percentage
      ]

      invalidMessages.forEach(msg => {
        ws.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify(msg)
        }))
      })

      // Valid message should still work
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'crawl_progress',
          data: { progressId, status: 'crawling', percentage: 50, logs: [] }
        })
      }))

      // Only the valid message should trigger callback
      expect(onMessage).toHaveBeenCalledTimes(1)
      expect(consoleWarn).toHaveBeenCalled()
    })

    it('should handle malformed JSON messages', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      // Send invalid JSON
      ws.onmessage?.(new MessageEvent('message', {
        data: 'invalid json'
      }))

      expect(onMessage).not.toHaveBeenCalled()
      expect(consoleError).toHaveBeenCalledWith(
        expect.stringContaining('Failed to parse progress message'),
        expect.any(Error)
      )
    })

    it('should handle WebSocket errors', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      const error = new Event('error')
      ws.onerror?.(error)

      expect(consoleError).toHaveBeenCalledWith(
        expect.stringContaining('Crawl progress WebSocket error'),
        error
      )
    })
  })

  describe('Connection Management', () => {
    it('should unsubscribe on cleanup', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      expect(ws.readyState).toBe(MockWebSocket.CONNECTING)

      crawlProgressService.disconnect()
      
      expect(ws.close).toHaveBeenCalled()
    })

    it('should reconnect on WebSocket disconnect', async () => {
      vi.useFakeTimers()
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage, {
        autoReconnect: true,
        reconnectDelay: 1000
      })

      // Simulate unexpected disconnect
      ws.onclose?.(new CloseEvent('close', { code: 1006, reason: 'Connection lost' }))

      expect(crawlProgressService.isReconnecting).toBe(true)
      expect(consoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Attempting to reconnect in 1000ms')
      )

      // Fast forward to trigger reconnection
      vi.advanceTimersByTime(1000)
      
      // Should create new connection
      expect(MockWebSocket).toHaveBeenCalledTimes(2)
      
      vi.useRealTimers()
    })

    it('should not reconnect on normal closure', () => {
      vi.useFakeTimers()
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage, {
        autoReconnect: true
      })

      // Simulate normal closure
      ws.onclose?.(new CloseEvent('close', { code: 1000, reason: 'Normal closure' }))

      expect(crawlProgressService.isReconnecting).toBe(false)
      
      // Should not attempt reconnection
      vi.advanceTimersByTime(5000)
      expect(MockWebSocket).toHaveBeenCalledTimes(1)
      
      vi.useRealTimers()
    })

    it('should handle completion event', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      const completionData: CrawlProgressData = {
        progressId,
        status: 'completed',
        percentage: 100,
        totalPages: 50,
        processedPages: 50,
        chunksStored: 250,
        wordCount: 25000,
        duration: '10m 15s',
        logs: ['Crawl completed successfully', 'Stored 250 chunks']
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'crawl_completed',
          data: completionData
        })
      }))

      expect(onMessage).toHaveBeenCalledWith(completionData)
      expect(onMessage.mock.calls[0][0].status).toBe('completed')
      expect(onMessage.mock.calls[0][0].percentage).toBe(100)
    })

    it('should detect stuck connections with heartbeat timeout', async () => {
      vi.useFakeTimers()
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      // Simulate connection open
      ws.onopen?.(new Event('open'))

      // No messages for 65 seconds should trigger timeout warning
      vi.advanceTimersByTime(65000)
      
      expect(consoleWarn).toHaveBeenCalledWith(
        expect.stringContaining('No messages received for')
      )
      
      vi.useRealTimers()
    })
  })

  describe('Message Filtering', () => {
    it('should ignore heartbeat and ping messages', () => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      // Send ping/pong/heartbeat messages
      const messageTypes = ['ping', 'pong', 'heartbeat']
      messageTypes.forEach((type: string) => {
        ws.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify({ type })
        }))
      })

      // These should not trigger the callback
      expect(onMessage).not.toHaveBeenCalled()
    })

    test.each([
      { type: 'crawl_progress', status: 'crawling' },
      { type: 'crawl_completed', status: 'completed' },
      { type: 'crawl_error', status: 'error' }
    ])('should handle $type messages', ({ type, status }: { type: string, status: string }) => {
      const progressId = 'crawl-123'
      const onMessage = vi.fn()
      
      const ws = crawlProgressService.streamProgress(progressId, onMessage)
      
      const data: CrawlProgressData = {
        progressId,
        status: status as any,
        percentage: 50,
        logs: [`Message type: ${type}`]
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({ type, data })
      }))

      expect(onMessage).toHaveBeenCalledWith(data)
    })
  })

  describe('Backward Compatibility', () => {
    test.each([
      { method: 'connect', args: ['progress-123'] },
      { method: 'onProgress', args: [vi.fn()] },
      { method: 'onCompleted', args: [vi.fn()] },
      { method: 'onError', args: [vi.fn()] },
      { method: 'removeProgressCallback', args: [vi.fn()] },
      { method: 'removeErrorCallback', args: [vi.fn()] }
    ])('should warn about deprecated $method', ({ method, args }: { method: string, args: any[] }) => {
      (crawlProgressService as any)[method](...args)
      
      expect(consoleWarn).toHaveBeenCalledWith(
        expect.stringContaining(`${method}() is deprecated`)
      )
    })
  })
})