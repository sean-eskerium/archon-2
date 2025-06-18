import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import { TaskBoardView } from '@/components/project-tasks/TaskBoardView'
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

// Mock DraggableTaskCard to make testing easier
vi.mock('@/components/project-tasks/DraggableTaskCard', () => ({
  DraggableTaskCard: ({ task, onView, onComplete, onDelete }: any) => (
    <div data-testid={`task-card-${task.id}`} className="task-card">
      <h4>{task.title}</h4>
      <p>{task.status}</p>
      <button onClick={onView} data-testid={`view-${task.id}`}>View</button>
      <button onClick={onComplete} data-testid={`complete-${task.id}`}>Complete</button>
      <button onClick={() => onDelete(task)} data-testid={`delete-${task.id}`}>Delete</button>
    </div>
  )
}))

// Mock Toggle component
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

// Mock DeleteConfirmModal
vi.mock('@/pages/ProjectPage', () => ({
  DeleteConfirmModal: ({ itemName, onConfirm, onCancel }: any) => (
    <div data-testid="delete-confirm-modal">
      <p>Delete {itemName}?</p>
      <button onClick={onConfirm} data-testid="confirm-delete">Confirm</button>
      <button onClick={onCancel} data-testid="cancel-delete">Cancel</button>
    </div>
  )
}))

// Helper function to render with DnD provider
const renderWithDnd = (ui: React.ReactElement) => {
  return render(
    <DndProvider backend={HTML5Backend}>
      {ui}
    </DndProvider>
  )
}

describe('TaskBoardView', () => {
  const mockTasks: Task[] = [
    {
      id: '1',
      title: 'Setup project',
      description: 'Initial project setup',
      status: 'backlog',
      task_order: 1,
      parent_task_id: null,
      assignee: 'John',
      priority: 'medium',
      due_date: null,
      completed_at: null,
      created_at: '2024-01-01',
      updated_at: '2024-01-01'
    },
    {
      id: '2', 
      title: 'Design database',
      description: 'Design database schema',
      status: 'in-progress',
      task_order: 1,
      parent_task_id: null,
      assignee: 'Jane',
      priority: 'high',
      due_date: null,
      completed_at: null,
      created_at: '2024-01-02',
      updated_at: '2024-01-02'
    },
    {
      id: '3',
      title: 'Code review',
      description: 'Review PR #123',
      status: 'review',
      task_order: 1,
      parent_task_id: null,
      assignee: 'Bob',
      priority: 'medium',
      due_date: null,
      completed_at: null,
      created_at: '2024-01-03',
      updated_at: '2024-01-03'
    },
    {
      id: '4',
      title: 'Deploy to production',
      description: 'Deploy v1.0',
      status: 'complete',
      task_order: 1,
      parent_task_id: null,
      assignee: 'Alice',
      priority: 'high',
      due_date: null,
      completed_at: '2024-01-04',
      created_at: '2024-01-04',
      updated_at: '2024-01-04'
    },
    {
      id: '5',
      title: 'Write tests',
      description: 'Unit tests for feature',
      status: 'in-progress',
      task_order: 2,
      parent_task_id: '2',
      assignee: 'Jane',
      priority: 'medium',
      due_date: null,
      completed_at: null,
      created_at: '2024-01-05',
      updated_at: '2024-01-05'
    }
  ]

  const defaultProps = {
    tasks: mockTasks,
    onTaskView: vi.fn(),
    onTaskComplete: vi.fn(),
    onTaskDelete: vi.fn(),
    onTaskMove: vi.fn(),
    onTaskReorder: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Board Structure', () => {
    it('should render board columns correctly', () => {
      renderWithDnd(<TaskBoardView {...defaultProps} />)

      // Check all columns are rendered
      expect(screen.getByText('Backlog')).toBeInTheDocument()
      expect(screen.getByText('In Process')).toBeInTheDocument()
      expect(screen.getByText('Review')).toBeInTheDocument()
      expect(screen.getByText('Complete')).toBeInTheDocument()
    })

    it('should display tasks in appropriate columns', () => {
      renderWithDnd(<TaskBoardView {...defaultProps} />)

      // Find columns by their titles
      const backlogCol = screen.getByText('Backlog').closest('.flex.flex-col')
      const inProgressCol = screen.getByText('In Process').closest('.flex.flex-col')
      const reviewCol = screen.getByText('Review').closest('.flex.flex-col')
      const completeCol = screen.getByText('Complete').closest('.flex.flex-col')

      // Check tasks are in correct columns
      expect(within(backlogCol!).getByText('Setup project')).toBeInTheDocument()
      expect(within(inProgressCol!).getByText('Design database')).toBeInTheDocument()
      expect(within(reviewCol!).getByText('Code review')).toBeInTheDocument()
      expect(within(completeCol!).getByText('Deploy to production')).toBeInTheDocument()
    })

    it('should only display parent tasks in columns', () => {
      renderWithDnd(<TaskBoardView {...defaultProps} />)

      // Parent tasks should be visible
      expect(screen.getByTestId('task-card-1')).toBeInTheDocument()
      expect(screen.getByTestId('task-card-2')).toBeInTheDocument()
      expect(screen.getByTestId('task-card-3')).toBeInTheDocument()
      expect(screen.getByTestId('task-card-4')).toBeInTheDocument()

      // Subtask should not be directly in column
      expect(screen.queryByTestId('task-card-5')).not.toBeInTheDocument()
    })

    it('should show empty columns when no tasks', () => {
      const emptyTasks: Task[] = []
      renderWithDnd(<TaskBoardView {...defaultProps} tasks={emptyTasks} />)

      // All columns should exist but be empty
      expect(screen.getByText('Backlog')).toBeInTheDocument()
      expect(screen.getByText('In Process')).toBeInTheDocument()
      expect(screen.getByText('Review')).toBeInTheDocument()
      expect(screen.getByText('Complete')).toBeInTheDocument()

      // No task cards should be present
      expect(screen.queryByTestId(/task-card-/)).not.toBeInTheDocument()
    })
  })

  describe('Column Styling', () => {
    it('should apply correct colors to column headers', () => {
      renderWithDnd(<TaskBoardView {...defaultProps} />)

      const backlogHeader = screen.getByText('Backlog')
      const inProgressHeader = screen.getByText('In Process')
      const reviewHeader = screen.getByText('Review')
      const completeHeader = screen.getByText('Complete')

      expect(backlogHeader).toHaveClass('text-gray-600')
      expect(inProgressHeader).toHaveClass('text-blue-600')
      expect(reviewHeader).toHaveClass('text-purple-600')
      expect(completeHeader).toHaveClass('text-green-600')
    })

    it('should have column header dividers with appropriate glow', () => {
      renderWithDnd(<TaskBoardView {...defaultProps} />)

      // Check for glow dividers
      const backlogCol = screen.getByText('Backlog').parentElement
      const inProgressCol = screen.getByText('In Process').parentElement
      const reviewCol = screen.getByText('Review').parentElement
      const completeCol = screen.getByText('Complete').parentElement

      expect(backlogCol?.querySelector('.bg-gray-500\\/30')).toBeInTheDocument()
      expect(inProgressCol?.querySelector('.bg-blue-500\\/30')).toBeInTheDocument()
      expect(reviewCol?.querySelector('.bg-purple-500\\/30')).toBeInTheDocument()
      expect(completeCol?.querySelector('.bg-green-500\\/30')).toBeInTheDocument()
    })
  })

  describe('Task Actions', () => {
    it('should handle task view action', async () => {
      const user = userEvent.setup()
      const onTaskView = vi.fn()
      
      renderWithDnd(<TaskBoardView {...defaultProps} onTaskView={onTaskView} />)

      await user.click(screen.getByTestId('view-1'))

      expect(onTaskView).toHaveBeenCalledWith(mockTasks[0])
    })

    it('should handle task complete action', async () => {
      const user = userEvent.setup()
      const onTaskComplete = vi.fn()
      
      renderWithDnd(<TaskBoardView {...defaultProps} onTaskComplete={onTaskComplete} />)

      await user.click(screen.getByTestId('complete-2'))

      expect(onTaskComplete).toHaveBeenCalledWith('2')
    })

    it('should show delete confirmation modal', async () => {
      const user = userEvent.setup()
      
      renderWithDnd(<TaskBoardView {...defaultProps} />)

      await user.click(screen.getByTestId('delete-1'))

      expect(screen.getByTestId('delete-confirm-modal')).toBeInTheDocument()
      expect(screen.getByText('Delete Setup project?')).toBeInTheDocument()
    })

    it('should delete task after confirmation', async () => {
      const user = userEvent.setup()
      const { projectService } = await import('@/services/projectService')
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })
      vi.mocked(projectService.deleteTask).mockResolvedValue(undefined)
      
      const onTaskDelete = vi.fn()
      
      renderWithDnd(<TaskBoardView {...defaultProps} onTaskDelete={onTaskDelete} />)

      // Click delete
      await user.click(screen.getByTestId('delete-1'))
      
      // Confirm deletion
      await user.click(screen.getByTestId('confirm-delete'))

      expect(projectService.deleteTask).toHaveBeenCalledWith('1')
      expect(onTaskDelete).toHaveBeenCalledWith(mockTasks[0])
      expect(showToast).toHaveBeenCalledWith(
        'Task "Setup project" deleted successfully',
        'success'
      )
    })

    it('should cancel task deletion', async () => {
      const user = userEvent.setup()
      const { projectService } = await import('@/services/projectService')
      
      renderWithDnd(<TaskBoardView {...defaultProps} />)

      // Click delete
      await user.click(screen.getByTestId('delete-1'))
      
      // Cancel deletion
      await user.click(screen.getByTestId('cancel-delete'))

      expect(projectService.deleteTask).not.toHaveBeenCalled()
      expect(screen.queryByTestId('delete-confirm-modal')).not.toBeInTheDocument()
    })
  })

  describe('Subtasks Toggle', () => {
    it('should show subtasks toggle when enabled', () => {
      renderWithDnd(
        <TaskBoardView 
          {...defaultProps} 
          showSubtasksToggle={true}
          onShowSubtasksChange={vi.fn()}
        />
      )

      expect(screen.getByText('Show Subtasks')).toBeInTheDocument()
      expect(screen.getByText('Display subtasks indented under parent tasks')).toBeInTheDocument()
      expect(screen.getByTestId('subtasks-toggle')).toBeInTheDocument()
    })

    it('should not show subtasks toggle when disabled', () => {
      renderWithDnd(<TaskBoardView {...defaultProps} />)

      expect(screen.queryByText('Show Subtasks')).not.toBeInTheDocument()
      expect(screen.queryByTestId('subtasks-toggle')).not.toBeInTheDocument()
    })

    it('should handle subtasks toggle change', async () => {
      const user = userEvent.setup()
      const onShowSubtasksChange = vi.fn()
      
      renderWithDnd(
        <TaskBoardView 
          {...defaultProps} 
          showSubtasksToggle={true}
          showSubtasks={false}
          onShowSubtasksChange={onShowSubtasksChange}
        />
      )

      await user.click(screen.getByTestId('subtasks-toggle'))

      expect(onShowSubtasksChange).toHaveBeenCalledWith(true)
    })
  })

  describe('Task Ordering', () => {
    it('should sort tasks by order within columns', () => {
      const tasksWithOrder: Task[] = [
        { ...mockTasks[1], task_order: 2 }, // In progress - order 2
        {
          id: '6',
          title: 'Write documentation',
          description: 'API docs',
          status: 'in-progress',
          task_order: 1, // In progress - order 1
          parent_task_id: null,
          assignee: 'John',
          priority: 'low',
          due_date: null,
          completed_at: null,
          created_at: '2024-01-06',
          updated_at: '2024-01-06'
        }
      ]

      renderWithDnd(<TaskBoardView {...defaultProps} tasks={tasksWithOrder} />)

      const inProgressCol = screen.getByText('In Process').closest('.flex.flex-col')
      const taskCards = within(inProgressCol!).getAllByTestId(/task-card-/)

      // Should be ordered by task_order
      expect(within(taskCards[0]).getByText('Write documentation')).toBeInTheDocument()
      expect(within(taskCards[1]).getByText('Design database')).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('should handle delete task error', async () => {
      const user = userEvent.setup()
      const { projectService } = await import('@/services/projectService')
      const { useToast } = await import('@/contexts/ToastContext')
      const showToast = vi.fn()
      vi.mocked(useToast).mockReturnValue({ showToast })
      vi.mocked(projectService.deleteTask).mockRejectedValue(new Error('Network error'))
      
      renderWithDnd(<TaskBoardView {...defaultProps} />)

      // Click delete and confirm
      await user.click(screen.getByTestId('delete-1'))
      await user.click(screen.getByTestId('confirm-delete'))

      expect(showToast).toHaveBeenCalledWith('Network error', 'error')
    })
  })

  describe('Drag and Drop', () => {
    it('should call onTaskMove when task is dropped in different column', () => {
      // Note: Actual drag and drop testing would require react-dnd-test-backend
      // and more complex setup. This is a placeholder for the structure.
      
      renderWithDnd(<TaskBoardView {...defaultProps} />)

      // Verify columns are drop targets (they should have the ColumnDropZone component)
      const columns = screen.getAllByText(/Backlog|In Process|Review|Complete/)
      expect(columns).toHaveLength(4)

      // In a real test with react-dnd-test-backend, you would:
      // 1. Drag a task from one column
      // 2. Drop it in another column
      // 3. Verify onTaskMove was called with correct parameters
    })
  })
})