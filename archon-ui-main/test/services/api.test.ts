import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import {
  retry,
  apiRequest,
  startMCPServer,
  stopMCPServer,
  getMCPServerStatus,
  crawlSinglePage,
  smartCrawlUrl,
  performRAGQuery,
  getAvailableSources,
  uploadDocument,
  getDatabaseMetrics
} from '@/services/api'
import type {
  MCPServerResponse,
  MCPServerStatus,
  CrawlResponse,
  RAGQueryResponse,
  SourcesResponse,
  UploadResponse,
  DatabaseMetrics
} from '@/services/api'

// Mock fetch globally
(globalThis as any).fetch = vi.fn()

describe('API Service', () => {
  let mockFetch: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch = vi.mocked((globalThis as any).fetch)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('retry utility', () => {
    it('should retry on failure and eventually succeed', async () => {
      let attempts = 0
      const fn = vi.fn(async () => {
        attempts++
        if (attempts < 3) throw new Error('fail')
        return 'success'
      })
      
      const result = await retry(fn, 3, 10)
      
      expect(result).toBe('success')
      expect(fn).toHaveBeenCalledTimes(3)
    })

    it('should throw after max retries', async () => {
      const fn = vi.fn(async () => {
        throw new Error('fail')
      })
      
      await expect(retry(fn, 2, 10)).rejects.toThrow('fail')
      expect(fn).toHaveBeenCalledTimes(2)
    })

    it('should use exponential backoff', async () => {
      vi.useFakeTimers()
      
      let attempts = 0
      const fn = vi.fn(async () => {
        attempts++
        if (attempts < 3) throw new Error('fail')
        return 'success'
      })
      
      const promise = retry(fn, 3, 100)
      
      // First attempt immediate
      await vi.runOnlyPendingTimersAsync()
      expect(fn).toHaveBeenCalledTimes(1)
      
      // Second attempt after 100ms
      await vi.advanceTimersByTimeAsync(100)
      expect(fn).toHaveBeenCalledTimes(2)
      
      // Third attempt after 200ms (100 * 2^1)
      await vi.advanceTimersByTimeAsync(200)
      expect(fn).toHaveBeenCalledTimes(3)
      
      const result = await promise
      expect(result).toBe('success')
      
      vi.useRealTimers()
    })
  })

  describe('apiRequest helper', () => {
    it('should make successful API requests', async () => {
      const mockResponse = { data: 'test' }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await apiRequest('/test')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should handle HTTP errors with error message', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Bad request' })
      })

      await expect(apiRequest('/test')).rejects.toThrow('Bad request')
    })

    it('should handle HTTP errors without JSON response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => {
          throw new Error('Invalid JSON')
        }
      })

      await expect(apiRequest('/test')).rejects.toThrow('Internal Server Error')
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(apiRequest('/test')).rejects.toThrow('Network error')
    })

    it('should merge custom headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      })

      await apiRequest('/test', {
        headers: { 'X-Custom': 'value' }
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-Custom': 'value'
          })
        })
      )
    })
  })

  describe('MCP Server Management', () => {
    it('should start MCP server', async () => {
      const mockResponse: MCPServerResponse = {
        success: true,
        status: 'starting',
        message: 'Server starting'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await startMCPServer()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/mcp/start',
        expect.objectContaining({
          method: 'POST'
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should stop MCP server', async () => {
      const mockResponse: MCPServerResponse = {
        success: true,
        status: 'stopped',
        message: 'Server stopped'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await stopMCPServer()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/mcp/stop',
        expect.objectContaining({
          method: 'POST'
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should get MCP server status', async () => {
      const mockStatus: MCPServerStatus = {
        status: 'running',
        uptime: 3600,
        logs: ['Server started', 'Processing requests']
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus
      })

      const result = await getMCPServerStatus()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/mcp/status',
        expect.any(Object)
      )
      expect(result).toEqual(mockStatus)
    })
  })

  describe('Crawling Operations', () => {
    it('should crawl single page', async () => {
      const mockResponse: CrawlResponse = {
        success: true,
        url: 'https://example.com',
        chunks_stored: 10,
        content_length: 5000
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await crawlSinglePage('https://example.com')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/crawl/single',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ url: 'https://example.com' })
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should perform smart crawl with options', async () => {
      const mockResponse: CrawlResponse = {
        success: true,
        url: 'https://example.com',
        urls_processed: 25,
        total_chunks: 150,
        crawl_type: 'smart'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await smartCrawlUrl('https://example.com', {
        max_depth: 3,
        max_concurrent: 5,
        chunk_size: 1000
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/crawl/smart',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            url: 'https://example.com',
            max_depth: 3,
            max_concurrent: 5,
            chunk_size: 1000
          })
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should handle crawl errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: 'Invalid URL' })
      })

      await expect(crawlSinglePage('invalid-url')).rejects.toThrow('Invalid URL')
    })
  })

  describe('RAG Operations', () => {
    it('should perform RAG query', async () => {
      const mockResponse: RAGQueryResponse = {
        query: 'How to use React hooks?',
        results: [
          {
            content: 'React hooks are functions that...',
            score: 0.95,
            source: 'react-docs'
          },
          {
            content: 'useEffect is a hook that...',
            score: 0.87,
            source: 'react-tutorial'
          }
        ]
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await performRAGQuery('How to use React hooks?', {
        source: 'react-docs',
        match_count: 5
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/rag/query',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            query: 'How to use React hooks?',
            source: 'react-docs',
            match_count: 5
          })
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should get available sources', async () => {
      const mockResponse: SourcesResponse = {
        sources: ['react-docs', 'vue-docs', 'angular-docs']
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await getAvailableSources()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/rag/sources',
        expect.any(Object)
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('Document Upload', () => {
    it('should upload document with metadata', async () => {
      const mockFile = new File(['test content'], 'test.pdf', {
        type: 'application/pdf'
      })
      
      const mockResponse: UploadResponse = {
        success: true,
        filename: 'test.pdf',
        chunks_created: 5
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await uploadDocument(mockFile, {
        tags: ['documentation', 'api'],
        knowledge_type: 'technical'
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/documents/upload',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
          headers: {}
        })
      )

      // Verify FormData contents
      const formData = mockFetch.mock.calls[0][1].body as FormData
      expect(formData.get('file')).toBe(mockFile)
      expect(formData.get('tags')).toBe(JSON.stringify(['documentation', 'api']))
      expect(formData.get('knowledge_type')).toBe('technical')

      expect(result).toEqual(mockResponse)
    })

    it('should upload document without metadata', async () => {
      const mockFile = new File(['test'], 'test.txt', {
        type: 'text/plain'
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, filename: 'test.txt' })
      })

      await uploadDocument(mockFile)

      const formData = mockFetch.mock.calls[0][1].body as FormData
      expect(formData.get('file')).toBe(mockFile)
      expect(formData.has('tags')).toBe(false)
      expect(formData.has('knowledge_type')).toBe(false)
    })

    it('should handle upload errors', async () => {
      const mockFile = new File([''], 'empty.txt')

      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: 'File too small' })
      })

      await expect(uploadDocument(mockFile)).rejects.toThrow('File too small')
    })
  })

  describe('Database Metrics', () => {
    it('should get database metrics', async () => {
      const mockMetrics: DatabaseMetrics = {
        documents: 1500,
        storage_used: '2.5 GB',
        last_sync: '2024-01-01T00:00:00Z'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics
      })

      const result = await getDatabaseMetrics()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/database/metrics',
        expect.any(Object)
      )
      expect(result).toEqual(mockMetrics)
    })
  })

  describe('Error Scenarios', () => {
    test.each([
      { fn: startMCPServer, name: 'startMCPServer' },
      { fn: stopMCPServer, name: 'stopMCPServer' },
      { fn: getMCPServerStatus, name: 'getMCPServerStatus' },
      { fn: getAvailableSources, name: 'getAvailableSources' },
      { fn: getDatabaseMetrics, name: 'getDatabaseMetrics' }
    ])('$name should retry on transient errors', async ({ fn }: { fn: () => Promise<any>, name: string }) => {
      // First two calls fail, third succeeds
      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Timeout'))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true })
        })

      const result = await fn()

      expect(mockFetch).toHaveBeenCalledTimes(3)
      expect(result).toBeTruthy()
    })

    it('should handle non-Error objects in catch', async () => {
      mockFetch.mockRejectedValueOnce('String error')

      await expect(apiRequest('/test')).rejects.toThrow('Unknown error occurred')
    })
  })
})
