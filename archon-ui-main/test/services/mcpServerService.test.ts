import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import { mcpServerService } from '@/services/mcpServerService'
import { MockWebSocket } from '../setup'
import type { ServerStatus, ServerResponse, LogEntry, ServerConfig } from '@/services/mcpServerService'

// Mock fetch globally
(globalThis as any).fetch = vi.fn()

describe('mcpServerService', () => {
  let mockFetch: ReturnType<typeof vi.fn>
  const baseUrl = 'http://localhost:8080'
  const wsUrl = 'ws://localhost:8080'
  
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch = vi.mocked((globalThis as any).fetch)
    // Reset server state
    mcpServerService.isReconnecting = false
  })

  afterEach(() => {
    vi.restoreAllMocks()
    mcpServerService.disconnectLogs()
  })

  describe('Server Lifecycle Management', () => {
    it('should start MCP server process', async () => {
      const mockResponse: ServerResponse = {
        success: true,
        status: 'starting',
        message: 'MCP server is starting'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await mcpServerService.startServer()

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/start`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }
      )
      expect(result.success).toBe(true)
      expect(result.status).toBe('starting')
    })

    it('should stop server gracefully with cleanup', async () => {
      const mockResponse: ServerResponse = {
        success: true,
        status: 'stopped',
        message: 'MCP server stopped successfully'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await mcpServerService.stopServer()

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/stop`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }
      )
      expect(result.status).toBe('stopped')
    })

    it('should prevent starting server when already running', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: 'Server already running' })
      })

      await expect(mcpServerService.startServer()).rejects.toThrow('Server already running')
    })

    it('should handle server start errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: 'Port already in use' })
      })

      await expect(mcpServerService.startServer()).rejects.toThrow('Port already in use')
    })
  })

  describe('Server Status Monitoring', () => {
    it('should get current server status', async () => {
      const mockStatus: ServerStatus = {
        status: 'running',
        uptime: 3600,
        logs: ['Server started', 'Listening on port 8051']
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus
      })

      const status = await mcpServerService.getStatus()

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/mcp/status`)
      expect(status.status).toBe('running')
      expect(status.uptime).toBe(3600)
    })

    test.each([
      { status: 'running' as const, uptime: 1000 },
      { status: 'starting' as const, uptime: null },
      { status: 'stopped' as const, uptime: null },
      { status: 'stopping' as const, uptime: 500 }
    ])('should handle $status status correctly', async ({ status, uptime }: { status: ServerStatus['status'], uptime: number | null }) => {
      const mockStatus: ServerStatus = {
        status,
        uptime,
        logs: []
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus
      })

      const result = await mcpServerService.getStatus()

      expect(result.status).toBe(status)
      expect(result.uptime).toBe(uptime)
    })
  })

  describe('Log Streaming', () => {
    it('should stream server logs through WebSocket', async () => {
      const onMessage = vi.fn()
      const mockLogs: LogEntry[] = [
        { timestamp: '2024-01-01T00:00:00Z', level: 'INFO', message: 'Server started' },
        { timestamp: '2024-01-01T00:00:01Z', level: 'DEBUG', message: 'Processing request' }
      ]

      const ws = mcpServerService.streamLogs(onMessage)
      
      expect(ws).toBeInstanceOf(MockWebSocket)
      expect(ws.url).toBe(`${wsUrl}/api/mcp/logs/stream`)

      // Simulate log messages
      mockLogs.forEach(log => {
        ws.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify(log)
        }))
      })

      expect(onMessage).toHaveBeenCalledTimes(2)
      expect(onMessage).toHaveBeenNthCalledWith(1, mockLogs[0])
      expect(onMessage).toHaveBeenNthCalledWith(2, mockLogs[1])
    })

    it('should ignore ping messages in log stream', async () => {
      const onMessage = vi.fn()
      
      const ws = mcpServerService.streamLogs(onMessage)
      
      // Send ping message
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({ type: 'ping' })
      }))

      expect(onMessage).not.toHaveBeenCalled()
    })

    it('should handle log stream reconnection', async () => {
      vi.useFakeTimers()
      const onMessage = vi.fn()
      
      const ws = mcpServerService.streamLogs(onMessage, {
        autoReconnect: true,
        reconnectDelay: 1000
      })

      // Simulate connection close
      ws.onclose?.(new CloseEvent('close'))

      expect(mcpServerService.isReconnecting).toBe(true)

      // Fast forward to trigger reconnection
      vi.advanceTimersByTime(1000)

      expect(mcpServerService.isReconnecting).toBe(false)
      
      vi.useRealTimers()
    })

    it('should fetch historical logs', async () => {
      const mockLogs: LogEntry[] = [
        { timestamp: '2024-01-01T00:00:00Z', level: 'INFO', message: 'Log 1' },
        { timestamp: '2024-01-01T00:00:01Z', level: 'ERROR', message: 'Log 2' }
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ logs: mockLogs })
      })

      const logs = await mcpServerService.getLogs({ limit: 100 })

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/mcp/logs?limit=100`)
      expect(logs).toEqual(mockLogs)
    })

    it('should clear server logs', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, message: 'Logs cleared' })
      })

      const result = await mcpServerService.clearLogs()

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/logs`,
        {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' }
        }
      )
      expect(result.success).toBe(true)
    })
  })

  describe('Configuration Management', () => {
    it('should get server configuration', async () => {
      const mockConfig: ServerConfig = {
        transport: 'sse',
        host: 'localhost',
        port: 8051,
        model: 'gpt-4'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockConfig
      })

      const config = await mcpServerService.getConfiguration()

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/mcp/config`)
      expect(config).toEqual(mockConfig)
    })

    it('should return default config if endpoint not available', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false
      })

      const config = await mcpServerService.getConfiguration()

      expect(config).toEqual({
        transport: 'sse',
        host: 'localhost',
        port: 8051
      })
    })

    it('should update server configuration', async () => {
      const updates: Partial<ServerConfig> = {
        port: 8052,
        model: 'claude-3'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, message: 'Configuration updated' })
      })

      const result = await mcpServerService.updateConfiguration(updates)

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/config`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates)
        }
      )
      expect(result.success).toBe(true)
    })
  })

  describe('Legacy MCP Tool Access', () => {
    beforeEach(() => {
      // Mock server is running
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'running', uptime: 100, logs: [] })
      })

      // Mock configuration
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ transport: 'sse', host: 'localhost', port: 8051 })
      })
    })

    it('should get available tools from Archon server', async () => {
      const mockTools = [
        {
          name: 'create_task',
          description: 'Create a new task',
          inputSchema: {
            type: 'object' as const,
            properties: {
              title: { type: 'string' }
            }
          }
        }
      ]

      // Mock the MCP response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          jsonrpc: '2.0',
          id: expect.any(String),
          result: { tools: mockTools }
        })
      })

      const tools = await mcpServerService.getAvailableTools()

      expect(tools).toEqual(mockTools)
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8051/sse',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('tools/list')
        })
      )
    })

    it('should call tool on Archon server', async () => {
      const toolName = 'create_task'
      const toolArgs = { title: 'New Task', description: 'Task description' }
      const mockResult = { task_id: 'task-123', success: true }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          jsonrpc: '2.0',
          id: expect.any(String),
          result: mockResult
        })
      })

      const result = await mcpServerService.callTool(toolName, toolArgs)

      expect(result).toEqual(mockResult)
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8051/sse',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('tools/call')
        })
      )
    })

    it('should handle MCP errors appropriately', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          jsonrpc: '2.0',
          id: '123',
          error: {
            code: -32601,
            message: 'Method not found'
          }
        })
      })

      await expect(mcpServerService.getAvailableTools()).rejects.toThrow('MCP Error: Method not found')
    })

    it('should require server to be running for MCP calls', async () => {
      // Override first mock to return stopped status
      mockFetch.mockReset()
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'stopped', uptime: null, logs: [] })
      })

      await expect(mcpServerService.getAvailableTools()).rejects.toThrow('MCP server is not running')
    })
  })

  describe('Error Handling', () => {
    test.each([
      {
        method: 'startServer',
        errorMessage: 'Failed to start MCP server'
      },
      {
        method: 'stopServer',
        errorMessage: 'Failed to stop MCP server'
      },
      {
        method: 'getStatus',
        errorMessage: 'Failed to get server status'
      },
      {
        method: 'getLogs',
        errorMessage: 'Failed to fetch logs'
      },
      {
        method: 'clearLogs',
        errorMessage: 'Failed to clear logs'
      }
    ])('should handle $method errors', async ({ method, errorMessage }: { method: string, errorMessage: string }) => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: null })
      })

      await expect((mcpServerService as any)[method]()).rejects.toThrow(errorMessage)
    })

    it('should handle WebSocket errors gracefully', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation()
      const onMessage = vi.fn()

      const ws = mcpServerService.streamLogs(onMessage)
      
      const error = new Event('error')
      ws.onerror?.(error)

      expect(consoleError).toHaveBeenCalledWith('WebSocket error:', error)
      
      consoleError.mockRestore()
    })

    it('should handle malformed log messages', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation()
      const onMessage = vi.fn()

      const ws = mcpServerService.streamLogs(onMessage)
      
      // Send invalid JSON
      ws.onmessage?.(new MessageEvent('message', {
        data: 'invalid json'
      }))

      expect(consoleError).toHaveBeenCalledWith('Failed to parse log message:', expect.any(Error))
      expect(onMessage).not.toHaveBeenCalled()
      
      consoleError.mockRestore()
    })
  })

  describe('Cleanup', () => {
    it('should clean up all resources on shutdown', () => {
      const onMessage = vi.fn()
      
      // Start log streaming
      const ws = mcpServerService.streamLogs(onMessage)
      expect(ws).toBeDefined()

      // Disconnect logs
      mcpServerService.disconnectLogs()

      // Verify WebSocket was closed
      expect(ws.close).toHaveBeenCalled()
    })

    it('should cancel reconnection attempts on disconnect', () => {
      vi.useFakeTimers()
      const onMessage = vi.fn()
      
      mcpServerService.streamLogs(onMessage, {
        autoReconnect: true,
        reconnectDelay: 5000
      })

      // Trigger reconnection
      mcpServerService.isReconnecting = true

      // Disconnect before reconnection happens
      mcpServerService.disconnectLogs()

      expect(mcpServerService.isReconnecting).toBe(false)
      
      vi.useRealTimers()
    })
  })
})