import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import { DraggableTaskCard } from '@/components/project-tasks/DraggableTaskCard'
import type { Task } from '@/components/project-tasks/TaskTableView'

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  Edit: ({ className }: any) => <span className={className} data-testid="edit-icon">✏</span>,
  Trash2: ({ className }: any) => <span className={className} data-testid="trash-icon">🗑</span>,
  RefreshCw: ({ className }: any) => <span className={className} data-testid="refresh-icon">↻</span>,
  Tag: ({ className }: any) => <span className={className} data-testid="tag-icon">🏷</span>,
  User: ({ className }: any) => <span className={className} data-testid="user-icon">👤</span>,
  Bot: ({ className }: any) => <span className={className} data-testid="bot-icon">🤖</span>,
  Clipboard: ({ className }: any) => <span className={className} data-testid="clipboard-icon">📋</span>
}))

// Mock task-utils
vi.mock('@/lib/task-utils', () => ({
  ItemTypes: { TASK: 'task' },
  getAssigneeIcon: (name: string) => {
    if (name === 'Archon') return <span data-testid="bot-icon">🤖</span>
    if (name === 'AI IDE Agent') return <span data-testid="ai-icon">🤖</span>
    return <span data-testid="user-icon">👤</span>
  },
  getAssigneeGlow: (name: string) => {
    if (name === 'Archon') return '0 0 10px rgba(236,72,153,0.5)'
    if (name === 'AI IDE Agent') return '0 0 10px rgba(16,185,129,0.5)'
    return '0 0 10px rgba(59,130,246,0.5)'
  },
  getOrderColor: (order: number) => {
    if (order <= 3) return 'bg-rose-400'
    if (order <= 6) return 'bg-orange-400'
    if (order <= 10) return 'bg-blue-400'
    return 'bg-emerald-400'
  },
  getOrderGlow: (order: number) => 'shadow-[0_0_10px_rgba(34,211,238,0.5)]'
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

describe('DraggableTaskCard', () => {
  const mockTask: Task = {
    id: '1',
    title: 'Setup project infrastructure',
    description: 'Initialize the project with necessary dependencies and configuration',
    status: 'in-progress',
    task_order: 2,
    assignee: { name: 'User', avatar: '' },
    feature: 'Core Setup',
    featureColor: '#3b82f6'
  }

  const mockSubtasks: Task[] = [
    {
      id: '2',
      title: 'Install dependencies',
      description: 'npm install all required packages',
      status: 'complete',
      task_order: 1,
      parent_task_id: '1',
      assignee: { name: 'AI IDE Agent', avatar: '' },
      feature: 'Core Setup',
      featureColor: '#3b82f6'
    },
    {
      id: '3',
      title: 'Configure ESLint',
      description: 'Setup linting rules',
      status: 'in-progress',
      task_order: 2,
      parent_task_id: '1',
      assignee: { name: 'Archon', avatar: '' },
      feature: 'Core Setup',
      featureColor: '#3b82f6'
    }
  ]

  const defaultProps = {
    task: mockTask,
    index: 0,
    onView: vi.fn(),
    onComplete: vi.fn(),
    onDelete: vi.fn(),
    onTaskReorder: vi.fn(),
    tasksInStatus: [mockTask]
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Card Display', () => {
    it('should render task card with details', () => {
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      expect(screen.getByText('Setup project infrastructure')).toBeInTheDocument()
      expect(screen.getByText('Core Setup')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument() // Task order
    })

    it('should display feature tag with color', () => {
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      const featureTag = screen.getByText('Core Setup').parentElement
      expect(featureTag).toHaveStyle({
        backgroundColor: '#3b82f620',
        color: '#3b82f6'
      })
    })

    it('should show assignee information', () => {
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      expect(screen.getByText('User')).toBeInTheDocument()
      expect(screen.getByTestId('user-icon')).toBeInTheDocument()
    })

    it('should display correct priority indicator color', () => {
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      // Task order 2 should have rose/red color
      const orderBadge = screen.getByText('2')
      expect(orderBadge).toHaveClass('bg-rose-400')
    })

    it('should show priority bar on left side', () => {
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      const priorityBar = document.querySelector('.absolute.left-0.top-0.bottom-0.w-\\[3px\\]')
      expect(priorityBar).toBeInTheDocument()
      expect(priorityBar).toHaveClass('bg-rose-400')
    })
  })

  describe('Card Actions', () => {
    it('should handle view/edit action', async () => {
      const user = userEvent.setup()
      const onView = vi.fn()
      
      renderWithDnd(<DraggableTaskCard {...defaultProps} onView={onView} />)

      const editButton = screen.getByTestId('edit-icon').parentElement
      await user.click(editButton!)

      expect(onView).toHaveBeenCalledOnce()
    })

    it('should handle delete action', async () => {
      const user = userEvent.setup()
      const onDelete = vi.fn()
      
      renderWithDnd(<DraggableTaskCard {...defaultProps} onDelete={onDelete} />)

      const deleteButton = screen.getByTestId('trash-icon').parentElement
      await user.click(deleteButton!)

      expect(onDelete).toHaveBeenCalledWith(mockTask)
    })

    it('should copy task ID to clipboard', async () => {
      const user = userEvent.setup()
      
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      const copyButton = screen.getByText('Task ID').parentElement
      await user.click(copyButton!)

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('1')
    })

    it('should show feedback when task ID is copied', async () => {
      const user = userEvent.setup()
      
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      const copyButton = screen.getByText('Task ID').parentElement
      await user.click(copyButton!)

      expect(screen.getByText('Copied!')).toBeInTheDocument()
    })
  })

  describe('Card Flipping', () => {
    it('should flip card when refresh button clicked', async () => {
      const user = userEvent.setup()
      
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      // Initially front side is visible
      expect(screen.getByTestId('tag-icon')).toBeInTheDocument()

      const flipButton = screen.getByTestId('refresh-icon').parentElement
      await user.click(flipButton!)

      // After flip, description should be visible on back
      expect(screen.getByText('Initialize the project with necessary dependencies and configuration')).toBeInTheDocument()
    })

    it('should flip back to front when clicked again', async () => {
      const user = userEvent.setup()
      
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      // Flip to back
      let flipButton = screen.getByTestId('refresh-icon').parentElement
      await user.click(flipButton!)

      // Flip back to front
      flipButton = screen.getByTestId('refresh-icon').parentElement
      await user.click(flipButton!)

      // Front side elements should be visible again
      expect(screen.getByTestId('tag-icon')).toBeInTheDocument()
    })
  })

  describe('Subtasks Display', () => {
    it('should show subtasks when enabled', () => {
      renderWithDnd(
        <DraggableTaskCard 
          {...defaultProps} 
          allTasks={[mockTask, ...mockSubtasks]}
          showSubtasks={true}
        />
      )

      expect(screen.getByText('Install dependencies')).toBeInTheDocument()
      expect(screen.getByText('Configure ESLint')).toBeInTheDocument()
    })

    it('should not show subtasks when disabled', () => {
      renderWithDnd(
        <DraggableTaskCard 
          {...defaultProps} 
          allTasks={[mockTask, ...mockSubtasks]}
          showSubtasks={false}
        />
      )

      // Subtasks container should be hidden
      const subtasksContainer = screen.getByText('Install dependencies').closest('.absolute.inset-0')?.parentElement
      expect(subtasksContainer).toHaveStyle({ display: 'none' })
    })

    it('should display subtask status badges', () => {
      renderWithDnd(
        <DraggableTaskCard 
          {...defaultProps} 
          allTasks={[mockTask, ...mockSubtasks]}
          showSubtasks={true}
        />
      )

      // Complete subtask
      const completeSubtask = screen.getByText('Install dependencies').parentElement
      expect(within(completeSubtask!).getByText('Complete')).toBeInTheDocument()

      // In progress subtask
      const inProgressSubtask = screen.getByText('Configure ESLint').parentElement
      expect(within(inProgressSubtask!).getByText('In Progress')).toBeInTheDocument()
    })

    it('should expand subtask on click', async () => {
      const user = userEvent.setup()
      
      renderWithDnd(
        <DraggableTaskCard 
          {...defaultProps} 
          allTasks={[mockTask, ...mockSubtasks]}
          showSubtasks={true}
        />
      )

      const subtask = screen.getByText('Install dependencies')
      
      // Initially truncated
      expect(subtask).toHaveClass('truncate')

      // Click to expand
      await user.click(subtask.parentElement!)

      // Should no longer be truncated
      expect(subtask).toHaveClass('whitespace-normal', 'break-words')
    })
  })

  describe('Hover Effects', () => {
    it('should highlight related tasks on hover', async () => {
      const user = userEvent.setup()
      const onTaskHover = vi.fn()
      
      renderWithDnd(
        <DraggableTaskCard 
          {...defaultProps}
          onTaskHover={onTaskHover}
          allTasks={[mockTask, ...mockSubtasks]}
        />
      )

      const card = screen.getByText('Setup project infrastructure').closest('.flip-card')
      
      await user.hover(card!)
      expect(onTaskHover).toHaveBeenCalledWith('1')

      await user.unhover(card!)
      expect(onTaskHover).toHaveBeenCalledWith(null)
    })

    it('should apply highlight glow when related task is hovered', () => {
      renderWithDnd(
        <DraggableTaskCard 
          {...defaultProps}
          hoveredTaskId='2' // Hovering a subtask
          allTasks={[mockTask, ...mockSubtasks]}
        />
      )

      const card = screen.getByText('Setup project infrastructure').closest('.flip-card')
      expect(card).toHaveClass('ring-1', 'ring-cyan-400/50')
    })
  })

  describe('Drag and Drop', () => {
    it('should be draggable', () => {
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      const card = screen.getByText('Setup project infrastructure').closest('.flip-card')
      expect(card).toHaveClass('cursor-move')
    })

    it('should show drag state', () => {
      // Note: Testing actual drag behavior would require react-dnd-test-backend
      // This test verifies the structure is in place
      
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      const card = screen.getByText('Setup project infrastructure').closest('.flip-card')
      expect(card).toBeDefined()
      
      // The card should have drag-related classes in its className
      expect(card?.className).toContain('cursor-move')
    })
  })

  describe('Assignee Display', () => {
    it('should show different icons for different assignees', () => {
      const archonTask = { ...mockTask, assignee: { name: 'Archon' as const, avatar: '' } }
      
      renderWithDnd(<DraggableTaskCard {...defaultProps} task={archonTask} />)

      expect(screen.getByText('Archon')).toBeInTheDocument()
      expect(screen.getAllByTestId('bot-icon')).toHaveLength(2) // Icon appears twice
    })

    it('should apply correct glow for assignee', () => {
      renderWithDnd(<DraggableTaskCard {...defaultProps} />)

      const assigneeIcon = screen.getByTestId('user-icon').parentElement
      expect(assigneeIcon).toHaveStyle({
        boxShadow: '0 0 10px rgba(59,130,246,0.5)'
      })
    })
  })
})