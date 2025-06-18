import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import { TaskTableView } from '@/components/project-tasks/TaskTableView'
import type { Task } from '@/components/project-tasks/TaskTableView'

// Mock dependencies
vi.mock('@/services/projectService', () => ({
  projectService: {
    deleteTask: vi.fn()
  }
}))

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

vi.mock('@/components/ui/Toggle', () => ({
  Toggle: ({ checked, onCheckedChange }: any) => (
    <button
      data-testid="subtasks-toggle"
      onClick={() => onCheckedChange(!checked)}
      aria-pressed={checked}
    >
      {checked ? 'Hide Subtasks' : 'Show Subtasks'}
    </button>
  )
}))

vi.mock('@/pages/ProjectPage', () => ({
  DeleteConfirmModal: ({ itemName, onConfirm, onCancel }: any) => (
    <div data-testid="delete-confirm-modal">
      <p>Delete {itemName}?</p>
      <button onClick={onConfirm} data-testid="confirm-delete">Confirm</button>
      <button onClick={onCancel} data-testid="cancel-delete">Cancel</button>
    </div>
  )
}))

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  Check: () => <span data-testid="check-icon">✓</span>,
  Trash2: () => <span data-testid="trash-icon">🗑</span>,
  Edit: () => <span data-testid="edit-icon">✏</span>,
  Tag: () => <span data-testid="tag-icon">🏷</span>,
  User: () => <span data-testid="user-icon">👤</span>,
  Bot: () => <span data-testid="bot-icon">🤖</span>,
  Clipboard: () => <span data-testid="clipboard-icon">📋</span>,
  Save: () => <span data-testid="save-icon">💾</span>,
  Plus: () => <span data-testid="plus-icon">➕</span>,
  List: () => <span data-testid="list-icon">📋</span>
}))

// Helper function to render with DnD provider
const renderWithDnd = (ui: React.ReactElement) => {
  return render(
    <DndProvider backend={HTML5Backend}>
      {ui}
    </DndProvider>
  )
}

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn(() => Promise.resolve())
  }
})

describe('TaskTableView', () => {
  const mockTasks: Task[] = [
    {
      id: '1',
      title: 'Setup project',
      description: 'Initial project setup',
      status: 'backlog',
      task_order: 1,
      assignee: { name: 'User', avatar: '' },
      feature: 'Core',
      featureColor: '#3b82f6'
    },
    {
      id: '2',
      title: 'Design database',
      description: 'Design database schema',
      status: 'in-progress',
      task_order: 1,
      assignee: { name: 'Archon', avatar: '' },
      feature: 'Backend',
      featureColor: '#10b981'
    },
    {
      id: '3',
      title: 'Code review',
      description: 'Review PR #123',
      status: 'review',
      task_order: 1,
      assignee: { name: 'AI IDE Agent', avatar: '' },
      feature: 'Quality',
      featureColor: '#f59e0b'
    },
    {
      id: '4',
      title: 'Deploy to production',
      description: 'Deploy v1.0',
      status: 'complete',
      task_order: 1,
      assignee: { name: 'User', avatar: '' },
      feature: 'DevOps',
      featureColor: '#8b5cf6'
    },
    {
      id: '5',
      title: 'Write tests',
      description: 'Unit tests for database',
      status: 'in-progress',
      task_order: 2,
      parent_task_id: '2',
      assignee: { name: 'Archon', avatar: '' },
      feature: 'Backend',
      featureColor: '#10b981'
    }
  ]

  const defaultProps = {
    tasks: mockTasks,
    onTaskView: vi.fn(),
    onTaskComplete: vi.fn(),
    onTaskDelete: vi.fn(),
    onTaskReorder: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Table Structure', () => {
    it('should render table with correct columns', () => {
      renderWithDnd(<TaskTableView {...defaultProps} />)

      // Check table headers
      expect(screen.getByText('Order')).toBeInTheDocument()
      expect(screen.getByText('Title')).toBeInTheDocument()
      expect(screen.getByText('Status')).toBeInTheDocument()
      expect(screen.getByText('Feature')).toBeInTheDocument()
      expect(screen.getByText('Assignee')).toBeInTheDocument()
      expect(screen.getByText('Actions')).toBeInTheDocument()
    })

    it('should display task data in rows', () => {
      renderWithDnd(<TaskTableView {...defaultProps} />)

      // Check task data
      expect(screen.getByText('Setup project')).toBeInTheDocument()
      expect(screen.getByText('Design database')).toBeInTheDocument()
      expect(screen.getByText('Code review')).toBeInTheDocument()
      expect(screen.getByText('Deploy to production')).toBeInTheDocument()
    })

    it('should show task order numbers', () => {
      renderWithDnd(<TaskTableView {...defaultProps} />)

      const rows = screen.getAllByRole('row').slice(1) // Skip header
      
      // First row should have order 1
      expect(within(rows[0]).getByText('1')).toBeInTheDocument()
    })

    it('should display appropriate colors for task orders', () => {
      renderWithDnd(<TaskTableView {...defaultProps} />)

      const orderCells = screen.getAllByText('1').filter(el => 
        el.closest('.rounded-full')
      )

      // Order 1-3 should have rose/red color
      expect(orderCells[0]).toHaveClass('text-rose-500')
    })
  })

  describe('Status Display and Filtering', () => {
    it('should show status filter dropdown', () => {
      renderWithDnd(<TaskTableView {...defaultProps} />)

      const statusFilter = screen.getByRole('combobox')
      expect(statusFilter).toBeInTheDocument()
      
      // Check options
      const options = within(statusFilter).getAllByRole('option')
      expect(options).toHaveLength(5) // All, Backlog, In Progress, Review, Complete
      expect(options[0]).toHaveTextContent('All Tasks')
    })

    it('should filter tasks by status', async () => {
      const user = userEvent.setup()
      renderWithDnd(<TaskTableView {...defaultProps} />)

      const statusFilter = screen.getByRole('combobox')
      
      // Filter by "In Progress"
      await user.selectOptions(statusFilter, 'in-progress')

      // Should only show in-progress tasks
      expect(screen.getByText('Design database')).toBeInTheDocument()
      expect(screen.queryByText('Setup project')).not.toBeInTheDocument()
      expect(screen.queryByText('Code review')).not.toBeInTheDocument()
    })

    it('should show status badges with correct colors', () => {
      renderWithDnd(<TaskTableView {...defaultProps} />)

      // Check for status text - these are in the editable cells
      const rows = screen.getAllByRole('row').slice(1) // Skip header
      
      expect(within(rows[0]).getByText('Backlog')).toBeInTheDocument()
      expect(within(rows[1]).getByText('In Progress')).toBeInTheDocument()
      expect(within(rows[2]).getByText('Review')).toBeInTheDocument()
      expect(within(rows[3]).getByText('Complete')).toBeInTheDocument()
    })
  })

  describe('Assignee Display', () => {
    it('should show assignee icons', () => {
      renderWithDnd(<TaskTableView {...defaultProps} />)

      // Icons are mocked, check they exist
      expect(screen.getAllByTestId('user-icon')).toHaveLength(2) // User assigned tasks
      expect(screen.getAllByTestId('bot-icon')).toHaveLength(2) // Archon assigned tasks
    })

    it('should show assignee tooltips', () => {
      renderWithDnd(<TaskTableView {...defaultProps} />)

      const assigneeIcons = screen.getAllByTitle(/Assignee:/)
      expect(assigneeIcons[0]).toHaveAttribute('title', 'Assignee: User')
      expect(assigneeIcons[1]).toHaveAttribute('title', 'Assignee: Archon')
      expect(assigneeIcons[2]).toHaveAttribute('title', 'Assignee: AI IDE Agent')
    })
  })

  describe('Row Actions', () => {
    it('should show action buttons on hover', async () => {
      const user = userEvent.setup()
      renderWithDnd(<TaskTableView {...defaultProps} />)

      const firstRow = screen.getAllByRole('row')[1] // First data row
      
      // Actions should be hidden initially (opacity-0)
      const actionsCell = within(firstRow).getAllByRole('cell')[5]
      const actionsContainer = within(actionsCell).getByRole('generic')
      expect(actionsContainer).toHaveClass('opacity-0')

      // Hover over row - actions should become visible
      await user.hover(firstRow)
      expect(actionsContainer).toHaveClass('group-hover:opacity-100')
    })

    it('should handle task deletion', async () => {
      const user = userEvent.setup()
      renderWithDnd(<TaskTableView {...defaultProps} />)

      const firstRow = screen.getAllByRole('row')[1]
      const deleteButton = within(firstRow).getByTestId('trash-icon').parentElement

      await user.click(deleteButton!)

      expect(defaultProps.onTaskDelete).toHaveBeenCalledWith(mockTasks[0])
    })

    it('should handle task completion', async () => {
      const user = userEvent.setup()
      renderWithDnd(<TaskTableView {...defaultProps} />)

      const firstRow = screen.getAllByRole('row')[1]
      const completeButton = within(firstRow).getByTestId('check-icon').parentElement

      await user.click(completeButton!)

      expect(defaultProps.onTaskComplete).toHaveBeenCalledWith('1')
    })

    it('should handle task view/edit', async () => {
      const user = userEvent.setup()
      renderWithDnd(<TaskTableView {...defaultProps} />)

      const firstRow = screen.getAllByRole('row')[1]
      const editButton = within(firstRow).getByTestId('edit-icon').parentElement

      await user.click(editButton!)

      expect(defaultProps.onTaskView).toHaveBeenCalledWith(mockTasks[0])
    })

    it('should copy task ID to clipboard', async () => {
      const user = userEvent.setup()
      renderWithDnd(<TaskTableView {...defaultProps} />)

      const firstRow = screen.getAllByRole('row')[1]
      const copyButton = within(firstRow).getByTestId('clipboard-icon').parentElement

      await user.click(copyButton!)

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('1')
    })
  })

  describe('Subtasks Display', () => {
    it('should show subtasks toggle when enabled', () => {
      renderWithDnd(
        <TaskTableView 
          {...defaultProps} 
          showSubtasksToggle={true}
          onShowSubtasksChange={vi.fn()}
        />
      )

      expect(screen.getByText('Show Subtasks')).toBeInTheDocument()
      expect(screen.getByTestId('subtasks-toggle')).toBeInTheDocument()
    })

    it('should show subtasks when toggled on', () => {
      renderWithDnd(
        <TaskTableView 
          {...defaultProps} 
          showSubtasks={true}
        />
      )

      // Subtask should be visible
      expect(screen.getByText('Write tests')).toBeInTheDocument()
    })

    it('should hide subtasks when toggled off', () => {
      renderWithDnd(
        <TaskTableView 
          {...defaultProps} 
          showSubtasks={false}
        />
      )

      // Subtask should not be visible
      expect(screen.queryByText('Write tests')).not.toBeInTheDocument()
    })

    it('should indent subtasks', () => {
      renderWithDnd(
        <TaskTableView 
          {...defaultProps} 
          showSubtasks={true}
        />
      )

      const subtaskRow = screen.getByText('Write tests').closest('tr')
      const titleCell = within(subtaskRow!).getByText('Write tests').parentElement

      // Should have indentation
      expect(titleCell).toHaveClass('ml-6')
    })
  })

  describe('Add Task Row', () => {
    it('should show add task row when onTaskCreate is provided', () => {
      renderWithDnd(
        <TaskTableView 
          {...defaultProps}
          onTaskCreate={vi.fn()}
        />
      )

      expect(screen.getByPlaceholderText('Type task title and press Enter...')).toBeInTheDocument()
    })

    it('should create new task on Enter', async () => {
      const user = userEvent.setup()
      const onTaskCreate = vi.fn().mockResolvedValue(undefined)
      
      renderWithDnd(
        <TaskTableView 
          {...defaultProps}
          onTaskCreate={onTaskCreate}
        />
      )

      const input = screen.getByPlaceholderText('Type task title and press Enter...')
      await user.type(input, 'New task{Enter}')

      expect(onTaskCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'New task',
          status: 'backlog',
          assignee: { name: 'AI IDE Agent', avatar: '' }
        })
      )
    })

    it('should calculate correct task order for new tasks', async () => {
      const user = userEvent.setup()
      const onTaskCreate = vi.fn().mockResolvedValue(undefined)
      
      renderWithDnd(
        <TaskTableView 
          {...defaultProps}
          onTaskCreate={onTaskCreate}
        />
      )

      // Filter to in-progress (has 2 tasks)
      const statusFilter = screen.getByRole('combobox')
      await user.selectOptions(statusFilter, 'in-progress')

      const input = screen.getByPlaceholderText('Type task title and press Enter...')
      await user.type(input, 'New task{Enter}')

      expect(onTaskCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          task_order: 3 // Should be after existing order 2
        })
      )
    })
  })

  describe('Empty State', () => {
    it('should show empty state when no tasks', () => {
      renderWithDnd(<TaskTableView {...defaultProps} tasks={[]} />)

      expect(screen.getByText('No tasks found')).toBeInTheDocument()
      expect(screen.getByText('Create your first task to get started')).toBeInTheDocument()
    })

    it('should show filtered empty state', async () => {
      const user = userEvent.setup()
      renderWithDnd(<TaskTableView {...defaultProps} />)

      // Filter to a status with no tasks
      const customTasks = mockTasks.filter(t => t.status !== 'backlog')
      renderWithDnd(<TaskTableView {...defaultProps} tasks={customTasks} />)

      const statusFilter = screen.getByRole('combobox')
      await user.selectOptions(statusFilter, 'backlog')

      expect(screen.getByText(/No tasks in Backlog/)).toBeInTheDocument()
    })
  })

  describe('Inline Editing', () => {
    it('should allow inline editing of task title', async () => {
      const user = userEvent.setup()
      const onTaskUpdate = vi.fn().mockResolvedValue(undefined)
      
      renderWithDnd(
        <TaskTableView 
          {...defaultProps}
          onTaskUpdate={onTaskUpdate}
        />
      )

      // Click on task title to edit
      const titleCell = screen.getByText('Setup project')
      await user.click(titleCell)

      // Should show input field
      const input = screen.getByDisplayValue('Setup project')
      expect(input).toBeInTheDocument()

      // Edit and save
      await user.clear(input)
      await user.type(input, 'Updated task{Enter}')

      expect(onTaskUpdate).toHaveBeenCalledWith('1', {
        title: 'Updated task'
      })
    })

    it('should allow changing task status inline', async () => {
      const user = userEvent.setup()
      const onTaskUpdate = vi.fn().mockResolvedValue(undefined)
      
      renderWithDnd(
        <TaskTableView 
          {...defaultProps}
          onTaskUpdate={onTaskUpdate}
        />
      )

      // Click on status to edit
      const statusCell = screen.getAllByText('Backlog')[0]
      await user.click(statusCell)

      // Should show select dropdown
      const select = screen.getByRole('combobox', { name: '' })
      await user.selectOptions(select, 'In Progress')

      expect(onTaskUpdate).toHaveBeenCalledWith('1', {
        status: 'in-progress'
      })
    })

    it('should cancel editing on Escape', async () => {
      const user = userEvent.setup()
      const onTaskUpdate = vi.fn()
      
      renderWithDnd(
        <TaskTableView 
          {...defaultProps}
          onTaskUpdate={onTaskUpdate}
        />
      )

      const titleCell = screen.getByText('Setup project')
      await user.click(titleCell)

      const input = screen.getByDisplayValue('Setup project')
      await user.clear(input)
      await user.type(input, 'Changed{Escape}')

      expect(onTaskUpdate).not.toHaveBeenCalled()
      expect(screen.getByText('Setup project')).toBeInTheDocument()
    })
  })

  describe('Sorting and Ordering', () => {
    it('should sort tasks by order within status groups', () => {
      const tasksWithOrder: Task[] = [
        { ...mockTasks[1], task_order: 2 },
        { 
          ...mockTasks[1], 
          id: '6', 
          title: 'First task',
          task_order: 1 
        }
      ]

      renderWithDnd(<TaskTableView {...defaultProps} tasks={tasksWithOrder} />)

      const rows = screen.getAllByRole('row').slice(1) // Skip header

      // First task should come first due to lower order
      expect(within(rows[0]).getByText('First task')).toBeInTheDocument()
      expect(within(rows[1]).getByText('Design database')).toBeInTheDocument()
    })
  })
})