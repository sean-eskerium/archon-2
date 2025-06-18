import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ToolTestingPanel } from '@/components/mcp/ToolTestingPanel'
import { mcpClientService } from '@/services/mcpClientService'
import type { Client, Tool } from '@/components/mcp/MCPClients'

// Mock dependencies
vi.mock('@/services/mcpClientService')

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  X: ({ className }: any) => <span className={className} data-testid="x-icon">X</span>,
  Play: ({ className }: any) => <span className={className} data-testid="play-icon">Play</span>,
  ChevronDown: ({ className }: any) => <span className={className} data-testid="chevron-icon">v</span>,
  TerminalSquare: ({ className }: any) => <span className={className} data-testid="terminal-icon">Terminal</span>,
  Copy: ({ className }: any) => <span className={className} data-testid="copy-icon">Copy</span>,
  Check: ({ className }: any) => <span className={className} data-testid="check-icon">Check</span>,
  MinusCircle: ({ className }: any) => <span className={className} data-testid="minus-icon">-</span>,
  Maximize2: ({ className }: any) => <span className={className} data-testid="maximize-icon">Maximize</span>,
  Minimize2: ({ className }: any) => <span className={className} data-testid="minimize-icon">Minimize</span>,
  Hammer: ({ className }: any) => <span className={className} data-testid="hammer-icon">Hammer</span>,
  GripHorizontal: ({ className }: any) => <span className={className} data-testid="grip-icon">Grip</span>
}))

describe('ToolTestingPanel', () => {
  const mockTools: Tool[] = [
    {
      id: 'tool-1',
      name: 'get_data',
      description: 'Retrieves data from the system',
      parameters: [
        { name: 'id', type: 'string', required: true, description: 'Data ID' },
        { name: 'format', type: 'string', required: false, description: 'Output format' }
      ]
    },
    {
      id: 'tool-2',
      name: 'calculate',
      description: 'Performs calculations',
      parameters: [
        { name: 'value', type: 'number', required: true, description: 'Input value' },
        { name: 'operation', type: 'string', required: true, description: 'Math operation' }
      ]
    },
    {
      id: 'tool-3',
      name: 'process_array',
      description: 'Process array data',
      parameters: [
        { name: 'items', type: 'array', required: true, description: 'Array of items' },
        { name: 'reverse', type: 'boolean', required: false, description: 'Reverse order' }
      ]
    }
  ]

  const mockClient: Client = {
    id: 'client-1',
    name: 'Test Client',
    status: 'online',
    ip: 'localhost:3000',
    lastSeen: '2024-01-01 12:00:00',
    version: '1.0.0',
    tools: mockTools
  }

  const mockOfflineClient: Client = {
    ...mockClient,
    status: 'offline',
    tools: []
  }

  const defaultProps = {
    client: mockClient,
    isOpen: true,
    onClose: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('Panel Display', () => {
    it('should render panel when open', () => {
      render(<ToolTestingPanel {...defaultProps} />)

      expect(screen.getByText('Test Client')).toBeInTheDocument()
      expect(screen.getByText('localhost:3000')).toBeInTheDocument()
      expect(screen.getByText('3 tools available')).toBeInTheDocument()
    })

    it('should not render when closed', () => {
      render(<ToolTestingPanel {...defaultProps} isOpen={false} />)

      expect(screen.queryByText('Test Client')).not.toBeInTheDocument()
    })

    it('should not render without client', () => {
      render(<ToolTestingPanel {...defaultProps} client={null} />)

      expect(screen.queryByText('Test Client')).not.toBeInTheDocument()
    })

    it('should show client status indicator', () => {
      render(<ToolTestingPanel {...defaultProps} />)

      // Online status should have cyan color
      const statusIndicator = screen.getByText('Test Client').previousElementSibling
      expect(statusIndicator).toHaveClass('bg-cyan-400')
    })

    it('should handle close button click', async () => {
      const user = userEvent.setup({ delay: null })
      const onClose = vi.fn()
      
      render(<ToolTestingPanel {...defaultProps} onClose={onClose} />)

      const closeButton = screen.getByRole('button', { name: 'Close panel' })
      await user.click(closeButton)

      expect(onClose).toHaveBeenCalledOnce()
    })
  })

  describe('Tool Selection', () => {
    it('should list available tools in dropdown', () => {
      render(<ToolTestingPanel {...defaultProps} />)

      const dropdown = screen.getByRole('combobox')
      expect(dropdown).toBeInTheDocument()

      // Check options
      const options = dropdown.querySelectorAll('option')
      expect(options).toHaveLength(3)
      expect(options[0]).toHaveTextContent('get_data')
      expect(options[1]).toHaveTextContent('calculate')
      expect(options[2]).toHaveTextContent('process_array')
    })

    it('should auto-select first tool', () => {
      render(<ToolTestingPanel {...defaultProps} />)

      const dropdown = screen.getByRole('combobox') as HTMLSelectElement
      expect(dropdown.value).toBe('tool-1')
      expect(screen.getByText('Retrieves data from the system')).toBeInTheDocument()
    })

    it('should display tool parameters when selected', () => {
      render(<ToolTestingPanel {...defaultProps} />)

      // First tool parameters should be shown
      expect(screen.getByText('Parameters')).toBeInTheDocument()
      expect(screen.getByText('id')).toBeInTheDocument()
      expect(screen.getByText('format')).toBeInTheDocument()
      
      // Required indicator
      const idLabel = screen.getByText('id')
      expect(idLabel.nextElementSibling).toHaveTextContent('*')
    })

    it('should change tool selection', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ToolTestingPanel {...defaultProps} />)

      const dropdown = screen.getByRole('combobox')
      await user.selectOptions(dropdown, 'tool-2')

      // Should show calculate tool info
      expect(screen.getByText('Performs calculations')).toBeInTheDocument()
      expect(screen.getByText('value')).toBeInTheDocument()
      expect(screen.getByText('operation')).toBeInTheDocument()
    })
  })

  describe('Parameter Input', () => {
    it('should render input fields for parameters', () => {
      render(<ToolTestingPanel {...defaultProps} />)

      // Check for input fields
      const idInput = screen.getByPlaceholderText('Enter string value')
      expect(idInput).toBeInTheDocument()
      expect(idInput.parentElement?.querySelector('label')).toHaveTextContent('id')
    })

    it('should show parameter descriptions', () => {
      render(<ToolTestingPanel {...defaultProps} />)

      expect(screen.getByText('Data ID')).toBeInTheDocument()
      expect(screen.getByText('Output format')).toBeInTheDocument()
    })

    it('should handle parameter value changes', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ToolTestingPanel {...defaultProps} />)

      const idInput = screen.getByPlaceholderText('Enter string value')
      await user.type(idInput, 'test-id-123')

      expect(idInput).toHaveValue('test-id-123')
    })

    it('should show appropriate input for different parameter types', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ToolTestingPanel {...defaultProps} />)

      // Select calculate tool with number parameter
      const dropdown = screen.getByRole('combobox')
      await user.selectOptions(dropdown, 'tool-2')

      const numberInput = screen.getByPlaceholderText('Enter number value')
      expect(numberInput).toBeInTheDocument()
    })

    it('should handle array parameter input', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ToolTestingPanel {...defaultProps} />)

      // Select process_array tool
      const dropdown = screen.getByRole('combobox')
      await user.selectOptions(dropdown, 'tool-3')

      const arrayInput = screen.getByPlaceholderText('Enter array (JSON or comma-separated)')
      await user.type(arrayInput, '["item1", "item2"]')

      expect(arrayInput).toHaveValue('["item1", "item2"]')
    })
  })

  describe('Tool Execution', () => {
    it('should execute tool with parameters', async () => {
      const user = userEvent.setup({ delay: null })
      vi.mocked(mcpClientService.callClientTool).mockResolvedValue({
        content: { text: 'Success result' }
      })

      render(<ToolTestingPanel {...defaultProps} />)

      // Enter parameter value
      const idInput = screen.getByPlaceholderText('Enter string value')
      await user.type(idInput, 'test-123')

      // Execute tool
      const executeButton = screen.getByRole('button', { name: /Execute Tool/i })
      await user.click(executeButton)

      expect(mcpClientService.callClientTool).toHaveBeenCalledWith({
        client_id: 'client-1',
        tool_name: 'get_data',
        arguments: { id: 'test-123' }
      })

      // Wait for result display
      vi.advanceTimersByTime(1000)
      
      await waitFor(() => {
        expect(screen.getByText(/Success result/)).toBeInTheDocument()
      })
    })

    it('should show loading state during execution', async () => {
      const user = userEvent.setup({ delay: null })
      vi.mocked(mcpClientService.callClientTool).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ content: 'Done' }), 1000))
      )

      render(<ToolTestingPanel {...defaultProps} />)

      const executeButton = screen.getByRole('button', { name: /Execute Tool/i })
      await user.click(executeButton)

      expect(screen.getByText('Executing...')).toBeInTheDocument()
      expect(executeButton).toBeDisabled()
    })

    it('should validate required parameters', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ToolTestingPanel {...defaultProps} />)

      // Don't fill required parameter
      const executeButton = screen.getByRole('button', { name: /Execute Tool/i })
      await user.click(executeButton)

      // Should show error in terminal
      await waitFor(() => {
        expect(screen.getByText(/Required parameter 'id' is missing/)).toBeInTheDocument()
      })

      expect(mcpClientService.callClientTool).not.toHaveBeenCalled()
    })

    it('should handle execution errors', async () => {
      const user = userEvent.setup({ delay: null })
      vi.mocked(mcpClientService.callClientTool).mockRejectedValue(
        new Error('Connection failed')
      )

      render(<ToolTestingPanel {...defaultProps} />)

      // Fill parameter and execute
      const idInput = screen.getByPlaceholderText('Enter string value')
      await user.type(idInput, 'test')
      
      await user.click(screen.getByRole('button', { name: /Execute Tool/i }))

      vi.advanceTimersByTime(1000)

      await waitFor(() => {
        expect(screen.getByText(/Connection failed/)).toBeInTheDocument()
      })
    })

    it('should convert parameter types correctly', async () => {
      const user = userEvent.setup({ delay: null })
      vi.mocked(mcpClientService.callClientTool).mockResolvedValue({ content: 'OK' })

      render(<ToolTestingPanel {...defaultProps} />)

      // Select calculate tool with number parameter
      await user.selectOptions(screen.getByRole('combobox'), 'tool-2')

      // Enter values
      const valueInput = screen.getAllByRole('textbox')[0]
      const operationInput = screen.getAllByRole('textbox')[1]
      
      await user.type(valueInput, '42')
      await user.type(operationInput, 'multiply')

      await user.click(screen.getByRole('button', { name: /Execute Tool/i }))

      expect(mcpClientService.callClientTool).toHaveBeenCalledWith({
        client_id: 'client-1',
        tool_name: 'calculate',
        arguments: {
          value: 42, // Should be converted to number
          operation: 'multiply'
        }
      })
    })
  })

  describe('Terminal Output', () => {
    it('should show initial terminal message', () => {
      render(<ToolTestingPanel {...defaultProps} />)

      expect(screen.getByText('> Tool testing terminal ready')).toBeInTheDocument()
    })

    it('should display execution command in terminal', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ToolTestingPanel {...defaultProps} />)

      const idInput = screen.getByPlaceholderText('Enter string value')
      await user.type(idInput, 'test-id')
      
      await user.click(screen.getByRole('button', { name: /Execute Tool/i }))

      await waitFor(() => {
        expect(screen.getByText(/execute get_data id=test-id/)).toBeInTheDocument()
      })
    })

    it('should clear terminal', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ToolTestingPanel {...defaultProps} />)

      // Add some output
      await user.click(screen.getByRole('button', { name: /Execute Tool/i }))
      
      vi.advanceTimersByTime(1000)

      // Clear terminal
      const clearButton = screen.getByRole('button', { name: 'Clear terminal' })
      await user.click(clearButton)

      expect(screen.getByText('> Terminal cleared')).toBeInTheDocument()
      expect(screen.queryByText('> Tool testing terminal ready')).not.toBeInTheDocument()
    })
  })

  describe('No Tools State', () => {
    it('should show empty state for offline client', () => {
      render(<ToolTestingPanel {...defaultProps} client={mockOfflineClient} />)

      expect(screen.getByText('No Tools Available')).toBeInTheDocument()
      expect(screen.getByText('Client is offline. Tools will be available when connected.')).toBeInTheDocument()
      expect(screen.getByTestId('hammer-icon')).toBeInTheDocument()
    })

    it('should show message when no tools discovered', () => {
      const clientNoTools = { ...mockClient, tools: [] }
      render(<ToolTestingPanel {...defaultProps} client={clientNoTools} />)

      expect(screen.getByText('No Tools Available')).toBeInTheDocument()
      expect(screen.getByText('No tools discovered for this client.')).toBeInTheDocument()
    })
  })

  describe('Panel Controls', () => {
    it('should toggle maximize/minimize', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ToolTestingPanel {...defaultProps} />)

      const panel = document.querySelector('[style*="height"]') as HTMLElement
      const initialHeight = panel.style.height

      // Maximize
      const maximizeButton = screen.getByRole('button', { name: 'Maximize panel' })
      await user.click(maximizeButton)

      expect(panel.style.height).not.toBe(initialHeight)
      expect(screen.getByRole('button', { name: 'Minimize panel' })).toBeInTheDocument()

      // Minimize back
      await user.click(screen.getByRole('button', { name: 'Minimize panel' }))
      expect(panel.style.height).toBe(initialHeight)
    })
  })
})