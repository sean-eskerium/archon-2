import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MCPClients } from '@/components/mcp/MCPClients'
import { mcpClientService } from '@/services/mcpClientService'
import type { MCPClient, MCPClientConfig } from '@/services/mcpClientService'
import React from 'react'

// Mock dependencies
vi.mock('@/services/mcpClientService')
vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

// Mock child components
vi.mock('@/components/mcp/ClientCard', () => ({
  ClientCard: ({ client, onSelect, onEdit, onDelete }: any) => (
    <div data-testid={`client-card-${client.id}`}>
      <h3>{client.name}</h3>
      <p>{client.status}</p>
      <p>{client.ip}</p>
      <button onClick={onSelect} data-testid={`select-${client.id}`}>Select</button>
      <button onClick={onEdit} data-testid={`edit-${client.id}`}>Edit</button>
      <button onClick={onDelete} data-testid={`delete-${client.id}`}>Delete</button>
    </div>
  )
}))

vi.mock('@/components/mcp/ToolTestingPanel', () => ({
  ToolTestingPanel: ({ client, isOpen, onClose }: any) => (
    isOpen ? (
      <div data-testid="tool-testing-panel">
        <h2>Tool Testing Panel</h2>
        {client && <p>Testing tools for: {client.name}</p>}
        <button onClick={onClose}>Close</button>
      </div>
    ) : null
  )
}))

vi.mock('@/pages/ProjectPage', () => ({
  DeleteConfirmModal: ({ itemName, onConfirm, onCancel }: any) => (
    <div data-testid="delete-confirm-modal">
      <p>Delete {itemName}?</p>
      <button onClick={onConfirm}>Confirm</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  )
}))

// Mock AddClientModal
const AddClientModal = ({ isOpen, onClose, onSubmit }: any) => {
  const [formData, setFormData] = React.useState({
    name: '',
    host: '',
    port: ''
  })
  const [error, setError] = React.useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name) {
      setError('Client name is required')
      return
    }
    await onSubmit({
      name: formData.name,
      transport_type: 'sse',
      connection_config: {
        host: formData.host,
        port: parseInt(formData.port),
        endpoint: '/sse'
      },
      auto_connect: true
    })
  }

  return (
    <div data-testid="add-client-modal">
      <form onSubmit={handleSubmit}>
        <input
          placeholder="Client Name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
        />
        <input
          placeholder="Host"
          value={formData.host}
          onChange={(e) => setFormData({ ...formData, host: e.target.value })}
        />
        <input
          placeholder="Port"
          value={formData.port}
          onChange={(e) => setFormData({ ...formData, port: e.target.value })}
        />
        {error && <p>{error}</p>}
        <button type="submit">Add Client</button>
      </form>
    </div>
  )
}

// Mock EditClientDrawer  
const EditClientDrawer = ({ client, isOpen, onClose, onUpdate }: any) => {
  if (!isOpen) return null
  
  return (
    <div data-testid="edit-client-drawer">
      <h2>Edit MCP Client</h2>
      <input defaultValue={client.name} />
      <button onClick={() => onUpdate({ ...client, name: 'Updated Archon' })}>Update Client</button>
    </div>
  )
}

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  Plus: ({ className }: any) => <span className={className} data-testid="plus-icon">+</span>,
  Settings: ({ className }: any) => <span className={className} data-testid="settings-icon">Settings</span>,
  Trash2: ({ className }: any) => <span className={className} data-testid="trash-icon">Trash</span>,
  X: ({ className }: any) => <span className={className} data-testid="x-icon">X</span>
}))

describe('MCPClients', () => {
  const mockClients: MCPClient[] = [
    {
      id: '1',
      name: 'Archon MCP Tools',
      status: 'connected',
      transport_type: 'sse',
      connection_config: {
        host: 'localhost',
        port: 3000,
        endpoint: '/sse'
      },
      auto_connect: true,
      created_at: new Date('2024-01-01'),
      updated_at: new Date('2024-01-01'),
      last_seen: new Date('2024-01-01T12:00:00'),
      last_error: null
    },
    {
      id: '2',
      name: 'Test Client',
      status: 'disconnected',
      transport_type: 'stdio',
      connection_config: {
        command: 'test-mcp',
        args: ['--verbose']
      },
      auto_connect: false,
      created_at: new Date('2024-01-02'),
      updated_at: new Date('2024-01-02'),
      last_seen: null,
      last_error: null
    },
    {
      id: '3',
      name: 'Error Client',
      status: 'error',
      transport_type: 'sse',
      connection_config: {
        host: 'error.host',
        port: 9999
      },
      auto_connect: true,
      created_at: new Date('2024-01-03'),
      updated_at: new Date('2024-01-03'),
      last_seen: new Date('2024-01-03'),
      last_error: 'Connection refused'
    }
  ]

  const mockTools = {
    tools: [
      {
        tool_name: 'get_project_info',
        tool_description: 'Get information about a project',
        tool_schema: {
          inputSchema: {
            type: 'object',
            properties: {
              project_id: { type: 'string', description: 'Project ID' }
            },
            required: ['project_id']
          }
        }
      },
      {
        tool_name: 'list_tasks',
        tool_description: 'List tasks for a project',
        tool_schema: {
          inputSchema: {
            type: 'object',
            properties: {
              project_id: { type: 'string' },
              status: { type: 'string' }
            },
            required: ['project_id']
          }
        }
      }
    ]
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    // Default mock implementations
    vi.mocked(mcpClientService.getClients).mockResolvedValue(mockClients)
    vi.mocked(mcpClientService.getClientTools).mockResolvedValue(mockTools)
    vi.mocked(mcpClientService.createClient).mockImplementation(async (config) => ({
      id: 'new-client',
      name: config.name,
      status: 'disconnected',
      transport_type: config.transport_type,
      connection_config: config.connection_config,
      auto_connect: config.auto_connect || false,
      created_at: new Date(),
      updated_at: new Date(),
      last_seen: null,
      last_error: null
    }))
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('Client Display', () => {
    it('should list all MCP clients', async () => {
      render(<MCPClients />)

      // Initially shows loading
      expect(screen.getByText('Loading MCP clients...')).toBeInTheDocument()

      // Wait for clients to load
      await waitFor(() => {
        expect(screen.getByTestId('client-card-1')).toBeInTheDocument()
      })

      // All clients should be displayed
      expect(screen.getByText('Archon MCP Tools')).toBeInTheDocument()
      expect(screen.getByText('Test Client')).toBeInTheDocument()
      expect(screen.getByText('Error Client')).toBeInTheDocument()
    })

    it('should display client status correctly', async () => {
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('client-card-1')).toBeInTheDocument()
      })

      // Check status mapping
      const archonCard = screen.getByTestId('client-card-1')
      expect(within(archonCard).getByText('online')).toBeInTheDocument()

      const testCard = screen.getByTestId('client-card-2')
      expect(within(testCard).getByText('offline')).toBeInTheDocument()

      const errorCard = screen.getByTestId('client-card-3')
      expect(within(errorCard).getByText('error')).toBeInTheDocument()
    })

    it('should display connection info', async () => {
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('client-card-1')).toBeInTheDocument()
      })

      // SSE client shows host:port
      expect(screen.getByText('localhost:3000')).toBeInTheDocument()

      // STDIO client shows command
      expect(screen.getByText('test-mcp')).toBeInTheDocument()

      // Error client shows host:port
      expect(screen.getByText('error.host:9999')).toBeInTheDocument()
    })

    it('should handle error state', async () => {
      vi.mocked(mcpClientService.getClients).mockRejectedValue(new Error('Network error'))

      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByText('Failed to load clients')).toBeInTheDocument()
      })

      // Dismiss button should work
      const dismissButton = screen.getByText('Dismiss')
      await userEvent.click(dismissButton)

      expect(screen.queryByText('Failed to load clients')).not.toBeInTheDocument()
    })
  })

  describe('Client Tools', () => {
    it('should load tools for connected clients', async () => {
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('client-card-1')).toBeInTheDocument()
      })

      // Tools should be loaded for connected client (Archon)
      expect(mcpClientService.getClientTools).toHaveBeenCalledWith('1')
    })

    it('should not load tools for disconnected clients', async () => {
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('client-card-2')).toBeInTheDocument()
      })

      // Tools should not be loaded for disconnected client
      expect(mcpClientService.getClientTools).not.toHaveBeenCalledWith('2')
    })

    it('should handle tool loading errors gracefully', async () => {
      vi.mocked(mcpClientService.getClientTools).mockRejectedValue(new Error('Tool load failed'))

      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('client-card-1')).toBeInTheDocument()
      })

      // Component should still render despite tool loading failure
      expect(screen.getByText('Archon MCP Tools')).toBeInTheDocument()
    })
  })

  describe('Add Client', () => {
    it('should show add client modal when button clicked', async () => {
      const user = userEvent.setup({ delay: null })
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByText('Add Client')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Add Client'))

      // Modal should appear
      expect(screen.getByTestId('add-client-modal')).toBeInTheDocument()
    })

    it('should add new MCP client with SSE transport', async () => {
      const user = userEvent.setup({ delay: null })
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByText('Add Client')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Add Client'))

      // Fill form
      const modal = screen.getByTestId('add-client-modal')
      await user.type(within(modal).getByPlaceholderText('Client Name'), 'New SSE Client')
      await user.type(within(modal).getByPlaceholderText('Host'), 'localhost')
      await user.type(within(modal).getByPlaceholderText('Port'), '4000')

      await user.click(within(modal).getByText('Add Client'))

      const expectedConfig: MCPClientConfig = {
        name: 'New SSE Client',
        transport_type: 'sse',
        connection_config: {
          host: 'localhost',
          port: 4000,
          endpoint: '/sse'
        },
        auto_connect: true
      }

      expect(mcpClientService.createClient).toHaveBeenCalledWith(expectedConfig)

      // New client should appear in list
      await waitFor(() => {
        expect(screen.getByText('New SSE Client')).toBeInTheDocument()
      })
    })

    it('should validate client configuration', async () => {
      const user = userEvent.setup({ delay: null })
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByText('Add Client')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Add Client'))

      const modal = screen.getByTestId('add-client-modal')
      
      // Try to submit empty form
      await user.click(within(modal).getByText('Add Client'))

      expect(screen.getByText('Client name is required')).toBeInTheDocument()
    })
  })

  describe('Edit Client', () => {
    it('should open edit drawer when edit button clicked', async () => {
      const user = userEvent.setup({ delay: null })
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('edit-1')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('edit-1'))

      expect(screen.getByTestId('edit-client-drawer')).toBeInTheDocument()
      expect(screen.getByText('Edit MCP Client')).toBeInTheDocument()
    })

    it('should update client configuration', async () => {
      const user = userEvent.setup({ delay: null })
      vi.mocked(mcpClientService.updateClient).mockResolvedValue({
        ...mockClients[0],
        name: 'Updated Archon'
      })

      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('edit-1')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('edit-1'))

      const drawer = screen.getByTestId('edit-client-drawer')
      const nameInput = within(drawer).getByDisplayValue('Archon MCP Tools')
      
      await user.clear(nameInput)
      await user.type(nameInput, 'Updated Archon')
      await user.click(within(drawer).getByText('Update Client'))

      expect(mcpClientService.updateClient).toHaveBeenCalledWith('1', expect.objectContaining({
        name: 'Updated Archon'
      }))

      await waitFor(() => {
        expect(screen.getByText('Updated Archon')).toBeInTheDocument()
      })
    })
  })

  describe('Delete Client', () => {
    it('should show confirmation modal before deleting', async () => {
      const user = userEvent.setup({ delay: null })
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('delete-2')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('delete-2'))

      expect(screen.getByTestId('delete-confirm-modal')).toBeInTheDocument()
      expect(screen.getByText('Delete Test Client?')).toBeInTheDocument()
    })

    it('should delete client after confirmation', async () => {
      const user = userEvent.setup({ delay: null })
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })

      vi.mocked(mcpClientService.deleteClient).mockResolvedValue(undefined)

      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('delete-2')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('delete-2'))
      await user.click(screen.getByText('Confirm'))

      expect(mcpClientService.deleteClient).toHaveBeenCalledWith('2')

      await waitFor(() => {
        expect(screen.queryByText('Test Client')).not.toBeInTheDocument()
      })

      expect(showToast).toHaveBeenCalledWith(
        'MCP Client "Test Client" deleted successfully',
        'success'
      )
    })

    it('should cancel deletion', async () => {
      const user = userEvent.setup({ delay: null })
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('delete-2')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('delete-2'))
      await user.click(screen.getByText('Cancel'))

      expect(mcpClientService.deleteClient).not.toHaveBeenCalled()
      expect(screen.getByText('Test Client')).toBeInTheDocument()
    })
  })

  describe('Tool Testing', () => {
    it('should open tool testing panel when client selected', async () => {
      const user = userEvent.setup({ delay: null })
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('select-1')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('select-1'))

      expect(screen.getByTestId('tool-testing-panel')).toBeInTheDocument()
      expect(screen.getByText('Testing tools for: Archon MCP Tools')).toBeInTheDocument()
    })

    it('should close tool testing panel', async () => {
      const user = userEvent.setup({ delay: null })
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('select-1')).toBeInTheDocument()
      })

      await user.click(screen.getByTestId('select-1'))
      await user.click(screen.getByText('Close'))

      expect(screen.queryByTestId('tool-testing-panel')).not.toBeInTheDocument()
    })
  })

  describe('Status Polling', () => {
    it('should refresh client statuses periodically', async () => {
      render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('client-card-1')).toBeInTheDocument()
      })

      // Clear initial calls
      vi.mocked(mcpClientService.getClients).mockClear()

      // Advance timer by 10 seconds
      vi.advanceTimersByTime(10000)

      // Should refresh statuses
      await waitFor(() => {
        expect(mcpClientService.getClients).toHaveBeenCalled()
      })
    })

    it('should clean up interval on unmount', async () => {
      const { unmount } = render(<MCPClients />)

      await waitFor(() => {
        expect(screen.getByTestId('client-card-1')).toBeInTheDocument()
      })

      const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
      
      unmount()

      expect(clearIntervalSpy).toHaveBeenCalled()
    })
  })
})