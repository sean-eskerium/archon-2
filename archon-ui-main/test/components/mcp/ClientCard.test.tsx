import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ClientCard } from '@/components/mcp/ClientCard'
import type { Client } from '@/components/mcp/MCPClients'

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  Server: ({ className }: any) => <span className={className} data-testid="server-icon">Server</span>,
  Activity: ({ className }: any) => <span className={className} data-testid="activity-icon">Activity</span>,
  Clock: ({ className }: any) => <span className={className} data-testid="clock-icon">Clock</span>,
  ChevronRight: ({ className }: any) => <span className={className} data-testid="chevron-icon">›</span>,
  Hammer: ({ className }: any) => <span className={className} data-testid="hammer-icon">Hammer</span>,
  Settings: ({ className }: any) => <span className={className} data-testid="settings-icon">Settings</span>,
  Trash2: ({ className }: any) => <span className={className} data-testid="trash-icon">Trash</span>
}))

describe('ClientCard', () => {
  const mockClient: Client = {
    id: '1',
    name: 'Test Client',
    status: 'online',
    ip: 'localhost:3000',
    lastSeen: '2024-01-01 12:00:00',
    version: '1.0.0',
    tools: [
      {
        id: 'tool-1',
        name: 'get_data',
        description: 'Retrieves data from the system',
        parameters: [
          { name: 'id', type: 'string', required: true }
        ]
      },
      {
        id: 'tool-2',
        name: 'process_data',
        description: 'Processes data according to specified rules',
        parameters: [
          { name: 'data', type: 'string', required: true },
          { name: 'options', type: 'array', required: false }
        ]
      }
    ]
  }

  const mockArchonClient: Client = {
    ...mockClient,
    id: 'archon-1',
    name: 'Archon MCP Tools',
    ip: 'localhost:8080'
  }

  const mockCallbacks = {
    onSelect: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Client Information Display', () => {
    it('should display client information', () => {
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      expect(screen.getByText('Test Client')).toBeInTheDocument()
      expect(screen.getByText('localhost:3000')).toBeInTheDocument()
      expect(screen.getByText('2024-01-01 12:00:00')).toBeInTheDocument()
      expect(screen.getByText('1.0.0')).toBeInTheDocument()
      expect(screen.getByText('2 available')).toBeInTheDocument()
    })

    it('should display last seen time', () => {
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      expect(screen.getByTestId('clock-icon')).toBeInTheDocument()
      expect(screen.getByText('Last seen:')).toBeInTheDocument()
    })

    it('should display version info', () => {
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      expect(screen.getByTestId('activity-icon')).toBeInTheDocument()
      expect(screen.getByText('Version:')).toBeInTheDocument()
    })

    it('should display tools count', () => {
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      expect(screen.getByTestId('hammer-icon')).toBeInTheDocument()
      expect(screen.getByText('Tools:')).toBeInTheDocument()
    })
  })

  describe('Status Display', () => {
    it('should show online status with correct styling', () => {
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      const statusBadge = screen.getByText('Online')
      expect(statusBadge).toBeInTheDocument()
      expect(statusBadge.parentElement).toHaveClass('bg-cyan-500/20', 'text-cyan-400')
    })

    it('should show offline status', () => {
      const offlineClient = { ...mockClient, status: 'offline' as const }
      render(
        <ClientCard 
          client={offlineClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      const statusBadge = screen.getByText('Offline')
      expect(statusBadge).toBeInTheDocument()
      expect(statusBadge.parentElement).toHaveClass('bg-gray-500/20', 'text-gray-400')
    })

    it('should show error status with error message', () => {
      const errorClient = { 
        ...mockClient, 
        status: 'error' as const,
        lastError: 'Connection refused'
      }
      render(
        <ClientCard 
          client={errorClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      const statusBadge = screen.getByText('Error')
      expect(statusBadge).toBeInTheDocument()
      expect(statusBadge.parentElement).toHaveClass('bg-pink-500/20', 'text-pink-400')
      
      // Error message should be displayed
      expect(screen.getByText('Last Error:')).toBeInTheDocument()
      expect(screen.getByText('Connection refused')).toBeInTheDocument()
    })
  })

  describe('Card Interactions', () => {
    it('should call onSelect when card is clicked', async () => {
      const user = userEvent.setup()
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      const card = screen.getByText('Test Client').closest('.flip-card')
      await user.click(card!)

      expect(mockCallbacks.onSelect).toHaveBeenCalledOnce()
    })

    it('should flip card when tools button is clicked', async () => {
      const user = userEvent.setup()
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      // Find the flip button (Hammer icon button)
      const flipButton = screen.getAllByRole('button').find(btn => 
        btn.getAttribute('title') === 'View available tools'
      )
      
      await user.click(flipButton!)

      // Should show tools on back side
      expect(screen.getByText('Available Tools (2)')).toBeInTheDocument()
      expect(screen.getByText('get_data')).toBeInTheDocument()
      expect(screen.getByText('process_data')).toBeInTheDocument()
    })

    it('should call onEdit when edit button is clicked', async () => {
      const user = userEvent.setup()
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
          onEdit={mockCallbacks.onEdit}
        />
      )

      const editButton = screen.getAllByRole('button').find(btn => 
        btn.getAttribute('title') === 'Edit client configuration'
      )
      
      await user.click(editButton!)

      expect(mockCallbacks.onEdit).toHaveBeenCalledWith(mockClient)
      expect(mockCallbacks.onSelect).not.toHaveBeenCalled()
    })

    it('should call onDelete when delete button is clicked', async () => {
      const user = userEvent.setup()
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
          onDelete={mockCallbacks.onDelete}
        />
      )

      const deleteButton = screen.getAllByRole('button').find(btn => 
        btn.getAttribute('title') === 'Delete client'
      )
      
      await user.click(deleteButton!)

      expect(mockCallbacks.onDelete).toHaveBeenCalledWith(mockClient)
      expect(mockCallbacks.onSelect).not.toHaveBeenCalled()
    })
  })

  describe('Tools Display', () => {
    it('should show tools on card back', async () => {
      const user = userEvent.setup()
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      // Flip to back
      const flipButton = screen.getAllByRole('button').find(btn => 
        btn.getAttribute('title') === 'View available tools'
      )
      await user.click(flipButton!)

      // Check tools are displayed
      expect(screen.getByText('get_data')).toBeInTheDocument()
      expect(screen.getByText('Retrieves data from the system')).toBeInTheDocument()
      expect(screen.getByText('1 parameter')).toBeInTheDocument()

      expect(screen.getByText('process_data')).toBeInTheDocument()
      expect(screen.getByText('Processes data according to specified rules')).toBeInTheDocument()
      expect(screen.getByText('2 parameters')).toBeInTheDocument()
    })

    it('should show message when no tools available', async () => {
      const user = userEvent.setup()
      const clientNoTools = { ...mockClient, tools: [] }
      
      render(
        <ClientCard 
          client={clientNoTools} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      // Flip to back
      const flipButton = screen.getAllByRole('button').find(btn => 
        btn.getAttribute('title') === 'View available tools'
      )
      await user.click(flipButton!)

      expect(screen.getByText('No tools discovered')).toBeInTheDocument()
    })

    it('should show offline message for offline client', async () => {
      const user = userEvent.setup()
      const offlineClient = { ...mockClient, status: 'offline' as const, tools: [] }
      
      render(
        <ClientCard 
          client={offlineClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      // Flip to back
      const flipButton = screen.getAllByRole('button').find(btn => 
        btn.getAttribute('title') === 'View available tools'
      )
      await user.click(flipButton!)

      expect(screen.getByText('Client offline - tools unavailable')).toBeInTheDocument()
    })
  })

  describe('Archon Client Special Features', () => {
    it('should apply special styling for Archon client', () => {
      render(
        <ClientCard 
          client={mockArchonClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      // Check for Archon-specific styling
      const clientName = screen.getByText('Archon MCP Tools')
      expect(clientName).toHaveClass('bg-gradient-to-r', 'from-blue-400', 'to-purple-500')

      // Should have Archon logo instead of server icon
      expect(screen.getByAltText('Archon')).toBeInTheDocument()
      expect(screen.getByAltText('Archon')).toHaveAttribute('src', '/logo-neon.svg')
    })

    it('should not show delete button for Archon client', () => {
      render(
        <ClientCard 
          client={mockArchonClient} 
          onSelect={mockCallbacks.onSelect}
          onDelete={mockCallbacks.onDelete}
        />
      )

      // Delete button should not exist for Archon client
      const deleteButton = screen.queryAllByRole('button').find(btn => 
        btn.getAttribute('title') === 'Delete client'
      )
      
      expect(deleteButton).not.toBeDefined()
    })

    it('should have order-first class for Archon client', () => {
      render(
        <ClientCard 
          client={mockArchonClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      const card = screen.getByText('Archon MCP Tools').closest('.flip-card')
      expect(card).toHaveClass('order-first')
    })
  })

  describe('Hover Effects', () => {
    it('should handle hover state', async () => {
      const user = userEvent.setup()
      render(
        <ClientCard 
          client={mockClient} 
          onSelect={mockCallbacks.onSelect}
        />
      )

      const card = screen.getByText('Test Client').closest('.flip-card')
      
      // Hover should add hover-lift class
      await user.hover(card!)
      
      const innerCard = card?.querySelector('[class*="transform-style-preserve-3d"]')
      expect(innerCard).toHaveClass('hover-lift')
    })
  })
})