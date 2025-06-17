import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import { mcpClientService } from '@/services/mcpClientService'
import type { MCPClient, MCPClientConfig, MCPClientTool, ToolCallRequest, ClientStatus } from '@/services/mcpClientService'

// Mock fetch globally
(globalThis as any).fetch = vi.fn()

describe('mcpClientService', () => {
  let mockFetch: ReturnType<typeof vi.fn>
  const baseUrl = 'http://localhost:8080'
  
  const mockClient: MCPClient = {
    id: 'client-123',
    name: 'Test MCP Client',
    transport_type: 'sse',
    connection_config: { url: 'http://example.com/mcp' },
    status: 'connected',
    auto_connect: true,
    health_check_interval: 30,
    last_seen: '2024-01-01T00:00:00Z',
    last_error: null,
    is_default: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch = vi.mocked((globalThis as any).fetch)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Client Management', () => {
    it('should list all available MCP clients', async () => {
      const mockClients: MCPClient[] = [mockClient, {
        ...mockClient,
        id: 'client-456',
        name: 'Another MCP Client',
        transport_type: 'stdio'
      }]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockClients
      })

      const clients = await mcpClientService.getClients()

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/mcp/clients/`)
      expect(clients).toHaveLength(2)
      expect(clients[0].name).toBe('Test MCP Client')
    })

    it('should create a new MCP client configuration', async () => {
      const newConfig: MCPClientConfig = {
        name: 'New MCP Client',
        transport_type: 'docker',
        connection_config: {
          container: 'mcp-server',
          command: ['python', 'server.py']
        },
        auto_connect: true,
        health_check_interval: 60
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockClient, ...newConfig, id: 'new-client-789' })
      })

      const result = await mcpClientService.createClient(newConfig)

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/clients/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newConfig)
        }
      )
      expect(result.name).toBe('New MCP Client')
      expect(result.transport_type).toBe('docker')
    })

    it('should update existing client settings', async () => {
      const updates = {
        name: 'Updated Client Name',
        auto_connect: false
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockClient, ...updates })
      })

      const result = await mcpClientService.updateClient('client-123', updates)

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/clients/client-123`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates)
        }
      )
      expect(result.name).toBe('Updated Client Name')
      expect(result.auto_connect).toBe(false)
    })

    it('should delete client', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, message: 'Client deleted' })
      })

      const result = await mcpClientService.deleteClient('client-123')

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/clients/client-123`,
        { method: 'DELETE' }
      )
      expect(result.success).toBe(true)
    })

    it('should get individual client details', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockClient
      })

      const client = await mcpClientService.getClient('client-123')

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/mcp/clients/client-123`)
      expect(client.id).toBe('client-123')
    })
  })

  describe('Transport Configuration Validation', () => {
    test.each([
      {
        transport_type: 'sse' as const,
        connection_config: { url: 'http://example.com/mcp' },
        valid: true
      },
      {
        transport_type: 'stdio' as const,
        connection_config: { command: ['python', 'server.py'] },
        valid: true
      },
      {
        transport_type: 'docker' as const,
        connection_config: { container: 'mcp-server', command: ['node', 'index.js'] },
        valid: true
      },
      {
        transport_type: 'npx' as const,
        connection_config: { package: '@example/mcp-server' },
        valid: true
      }
    ])('should validate $transport_type transport configuration', async ({ transport_type, connection_config }: { transport_type: 'sse' | 'stdio' | 'docker' | 'npx', connection_config: Record<string, any> }) => {
      const config: MCPClientConfig = {
        name: 'Test Client',
        transport_type,
        connection_config
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, message: 'Configuration is valid' })
      })

      const result = await mcpClientService.testClientConfig(config)

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/clients/test-config`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config)
        }
      )
      expect(result.success).toBe(true)
    })
  })

  describe('Connection Management', () => {
    it('should connect to MCP client', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, message: 'Connected successfully' })
      })

      const result = await mcpClientService.connectClient('client-123')

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/clients/client-123/connect`,
        { method: 'POST' }
      )
      expect(result.success).toBe(true)
    })

    it('should disconnect from MCP client', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, message: 'Disconnected successfully' })
      })

      const result = await mcpClientService.disconnectClient('client-123')

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/clients/client-123/disconnect`,
        { method: 'POST' }
      )
      expect(result.success).toBe(true)
    })

    it('should get client connection status', async () => {
      const mockStatus: ClientStatus = {
        client_id: 'client-123',
        status: 'connected',
        last_seen: '2024-01-01T00:00:00Z',
        last_error: null,
        is_active: true
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus
      })

      const status = await mcpClientService.getClientStatus('client-123')

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/mcp/clients/client-123/status`)
      expect(status.is_active).toBe(true)
    })

    it('should handle connection errors gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Connection refused' })
      })

      await expect(
        mcpClientService.connectClient('client-123')
      ).rejects.toThrow('Connection refused')
    })

    it('should auto-connect to clients marked with auto_connect', async () => {
      const mockClients: MCPClient[] = [
        { ...mockClient, auto_connect: true },
        { ...mockClient, id: 'client-456', auto_connect: false },
        { ...mockClient, id: 'client-789', auto_connect: true }
      ]

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockClients
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true, message: 'Connected' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true, message: 'Connected' })
        })

      const results = await mcpClientService.autoConnectClients()

      expect(results).toHaveLength(2)
      expect(results[0].clientId).toBe('client-123')
      expect(results[1].clientId).toBe('client-789')
    })
  })

  describe('Tool Discovery & Execution', () => {
    const mockTools: MCPClientTool[] = [
      {
        id: 'tool-1',
        client_id: 'client-123',
        tool_name: 'get_weather',
        tool_description: 'Get current weather',
        tool_schema: {
          type: 'object',
          properties: {
            location: { type: 'string' }
          },
          required: ['location']
        },
        discovered_at: '2024-01-01T00:00:00Z'
      }
    ]

    it('should discover tools from connected client', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          client_id: 'client-123',
          tools: mockTools,
          count: 1
        })
      })

      const result = await mcpClientService.discoverClientTools('client-123')

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/clients/client-123/tools/discover`,
        { method: 'POST' }
      )
      expect(result.tools).toHaveLength(1)
      expect(result.tools[0].tool_name).toBe('get_weather')
    })

    it('should get cached tools from client', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          client_id: 'client-123',
          tools: mockTools,
          count: 1
        })
      })

      const result = await mcpClientService.getClientTools('client-123')

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/mcp/clients/client-123/tools`)
      expect(result.tools).toHaveLength(1)
    })

    it('should call tool with arguments', async () => {
      const toolRequest: ToolCallRequest = {
        client_id: 'client-123',
        tool_name: 'get_weather',
        arguments: { location: 'San Francisco' }
      }

      const mockResponse = {
        result: { temperature: 72, condition: 'sunny' }
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await mcpClientService.callClientTool(toolRequest)

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/clients/tools/call`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(toolRequest)
        }
      )
      expect(result.result.temperature).toBe(72)
    })

    it('should get all available tools from all clients', async () => {
      const mockAllTools = {
        archon_tools: [
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
        ],
        client_tools: [
          {
            client: mockClient,
            tools: mockTools
          }
        ],
        total_count: 2
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAllTools
      })

      const result = await mcpClientService.getAllAvailableTools()

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/mcp/clients/tools/all`)
      expect(result.total_count).toBe(2)
      expect(result.archon_tools).toHaveLength(1)
      expect(result.client_tools).toHaveLength(1)
    })
  })

  describe('Batch Operations', () => {
    it('should connect to multiple clients concurrently', async () => {
      const clientIds = ['client-1', 'client-2', 'client-3']

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true, message: 'Connected' })
        })
        .mockResolvedValueOnce({
          ok: false,
          json: async () => ({ detail: 'Connection failed' })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true, message: 'Connected' })
        })

      const results = await mcpClientService.connectMultipleClients(clientIds)

      expect(results).toHaveLength(3)
      expect(results[0]).toMatchObject({ clientId: 'client-1', success: true })
      expect(results[1]).toMatchObject({ clientId: 'client-2', success: false })
      expect(results[2]).toMatchObject({ clientId: 'client-3', success: true })
    })

    it('should get status for all clients', async () => {
      const mockClients: MCPClient[] = [
        mockClient,
        { ...mockClient, id: 'client-456' }
      ]

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockClients
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            client_id: 'client-123',
            status: 'connected',
            is_active: true,
            last_seen: '2024-01-01T00:00:00Z',
            last_error: null
          })
        })
        .mockResolvedValueOnce({
          ok: false,
          json: async () => ({ detail: 'Client not found' })
        })

      const results = await mcpClientService.getAllClientStatuses()

      expect(results).toHaveLength(2)
      expect(results[0].status.is_active).toBe(true)
      expect(results[1].status.status).toBe('error')
    })
  })

  describe('Archon Integration', () => {
    it('should create Archon MCP client with docker transport', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...mockClient,
          name: 'Archon',
          transport_type: 'docker',
          is_default: true
        })
      })

      const result = await mcpClientService.createArchonClient()

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/mcp/clients/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: 'Archon',
            transport_type: 'docker',
            connection_config: {
              container: 'archon-pyserver',
              command: ['python', '/app/src/main.py'],
              working_dir: '/app'
            },
            auto_connect: true,
            health_check_interval: 30,
            is_default: true
          })
        }
      )
      expect(result.name).toBe('Archon')
      expect(result.is_default).toBe(true)
    })

    it('should get or create Archon client', async () => {
      // First call returns empty list
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => []
      })

      // Second call creates new Archon client
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...mockClient,
          name: 'Archon',
          is_default: true
        })
      })

      const result = await mcpClientService.getOrCreateArchonClient()

      expect(mockFetch).toHaveBeenCalledTimes(2)
      expect(result.name).toBe('Archon')
    })

    it('should return existing Archon client if found', async () => {
      const archonClient = {
        ...mockClient,
        name: 'Archon',
        is_default: true
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [archonClient, mockClient]
      })

      const result = await mcpClientService.getOrCreateArchonClient()

      expect(mockFetch).toHaveBeenCalledTimes(1)
      expect(result).toEqual(archonClient)
    })
  })

  describe('Error Handling', () => {
    test.each([
      {
        method: 'getClients',
        args: [],
        errorMessage: 'Failed to get MCP clients'
      },
      {
        method: 'createClient',
        args: [{ name: 'Test', transport_type: 'sse' as const, connection_config: {} }],
        errorMessage: 'Failed to create MCP client'
      },
      {
        method: 'getClient',
        args: ['client-123'],
        errorMessage: 'Failed to get MCP client'
      },
      {
        method: 'updateClient',
        args: ['client-123', { name: 'Updated' }],
        errorMessage: 'Failed to update MCP client'
      },
      {
        method: 'deleteClient',
        args: ['client-123'],
        errorMessage: 'Failed to delete MCP client'
      }
    ])('should handle $method errors', async ({ method, args, errorMessage }: { method: string, args: any[], errorMessage: string }) => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: null })
      })

      await expect(
        (mcpClientService as any)[method](...args)
      ).rejects.toThrow(errorMessage)
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(
        mcpClientService.getClients()
      ).rejects.toThrow('Network error')
    })

    it('should handle custom error messages from API', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Custom error message' })
      })

      await expect(
        mcpClientService.connectClient('client-123')
      ).rejects.toThrow('Custom error message')
    })
  })
})