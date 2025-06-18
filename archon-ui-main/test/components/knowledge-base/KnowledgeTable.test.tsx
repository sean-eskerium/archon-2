import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { KnowledgeTable } from '@/components/knowledge-base/KnowledgeTable'
import type { KnowledgeItem } from '@/services/knowledgeBaseService'

// Mock dependencies
vi.mock('lucide-react', () => ({
  Link: ({ className }: any) => <span className={className} data-testid="link-icon">Link</span>,
  Upload: ({ className }: any) => <span className={className} data-testid="upload-icon">Upload</span>,
  Trash2: ({ className }: any) => <span className={className} data-testid="trash-icon">Trash</span>,
  RefreshCw: ({ className }: any) => <span className={className} data-testid="refresh-icon">RefreshCw</span>,
  X: ({ className }: any) => <span className={className} data-testid="x-icon">X</span>,
  Globe: ({ className }: any) => <span className={className} data-testid="globe-icon">Globe</span>,
  BoxIcon: ({ className }: any) => <span className={className} data-testid="box-icon">Box</span>,
  Brain: ({ className }: any) => <span className={className} data-testid="brain-icon">Brain</span>
}))

vi.mock('date-fns', () => ({
  format: (date: Date, formatStr: string) => {
    // Simple mock format
    const d = new Date(date)
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return `${months[d.getMonth()]} ${d.getDate().toString().padStart(2, '0')}, ${d.getFullYear()}`
  }
}))

describe('KnowledgeTable', () => {
  const mockKnowledgeItems: KnowledgeItem[] = [
    {
      id: '1',
      source_id: 'source-1',
      title: 'React Documentation',
      url: 'https://react.dev/learn',
      metadata: {
        source_type: 'url',
        knowledge_type: 'technical',
        status: 'active',
        tags: ['react', 'frontend', 'javascript'],
        chunks_count: 45,
        update_frequency: 7
      },
      created_at: '2024-01-01T10:00:00Z',
      updated_at: '2024-01-15T14:30:00Z'
    },
    {
      id: '2',
      source_id: 'source-2',
      title: 'React Hooks Guide',
      url: 'https://react.dev/reference/react',
      metadata: {
        source_type: 'url',
        knowledge_type: 'technical',
        status: 'active',
        tags: ['react', 'hooks'],
        chunks_count: 30,
        update_frequency: 7
      },
      created_at: '2024-01-02T10:00:00Z',
      updated_at: '2024-01-16T10:00:00Z'
    },
    {
      id: '3',
      source_id: 'source-3',
      title: 'System Design Concepts',
      url: 'file://system-design.pdf',
      metadata: {
        source_type: 'file',
        knowledge_type: 'technical',
        status: 'processing',
        tags: ['architecture', 'design'],
        chunks_count: 120,
        update_frequency: 0
      },
      created_at: '2024-01-03T10:00:00Z',
      updated_at: '2024-01-03T10:30:00Z'
    },
    {
      id: '4',
      source_id: 'source-4',
      title: 'TypeScript Handbook',
      url: 'https://www.typescriptlang.org/docs/',
      metadata: {
        source_type: 'url',
        knowledge_type: 'technical',
        status: 'error',
        tags: ['typescript', 'types'],
        chunks_count: 0,
        update_frequency: 30
      },
      created_at: '2024-01-04T10:00:00Z',
      updated_at: '2024-01-04T10:00:00Z'
    }
  ]

  const mockOnDelete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Table Display', () => {
    it('should display knowledge entries in a table', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // Check table structure
      expect(screen.getByRole('table')).toBeInTheDocument()
      
      // Check headers
      expect(screen.getByText('Title')).toBeInTheDocument()
      expect(screen.getByText('Type')).toBeInTheDocument()
      expect(screen.getByText('Tags')).toBeInTheDocument()
      expect(screen.getByText('Sources')).toBeInTheDocument()
      expect(screen.getByText('Chunks')).toBeInTheDocument()
      expect(screen.getByText('Updated')).toBeInTheDocument()
      expect(screen.getByText('Frequency')).toBeInTheDocument()
      expect(screen.getByText('Status')).toBeInTheDocument()
    })

    it('should group URL entries by domain', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // react.dev items should be grouped
      const reactDevRow = screen.getByText('react.dev').closest('tr')
      expect(reactDevRow).toBeInTheDocument()
      
      // Should show grouped count
      const groupedBadge = within(reactDevRow!).getByText('2')
      expect(groupedBadge).toBeInTheDocument()
      expect(groupedBadge.parentElement).toHaveClass('bg-blue-500/20')
    })

    it('should not group file uploads', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // File upload should appear separately
      expect(screen.getByText('System Design Concepts')).toBeInTheDocument()
    })

    it('should display correct icons for different source types', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // URL items should have link icon
      const reactRow = screen.getByText('react.dev').closest('tr')
      expect(within(reactRow!).getByTestId('link-icon')).toBeInTheDocument()

      // File uploads should have upload icon
      const fileRow = screen.getByText('System Design Concepts').closest('tr')
      expect(within(fileRow!).getByTestId('upload-icon')).toBeInTheDocument()
    })
  })

  describe('Metadata Display', () => {
    it('should display knowledge type badges', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // Technical type
      const technicalBadges = screen.getAllByText('technical')
      expect(technicalBadges.length).toBeGreaterThan(0)
      expect(technicalBadges[0].parentElement).toHaveClass('bg-blue-100')

      // Concept type
      const conceptBadge = screen.getByText('concept')
      expect(conceptBadge.parentElement).toHaveClass('bg-purple-100')
    })

    it('should display type icons', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // Technical items should have box icon
      const reactRow = screen.getByText('react.dev').closest('tr')
      expect(within(reactRow!).getByTestId('box-icon')).toBeInTheDocument()

      // Concept items should have brain icon
      const conceptRow = screen.getByText('System Design Concepts').closest('tr')
      expect(within(conceptRow!).getByTestId('brain-icon')).toBeInTheDocument()
    })

    it('should display tags with overflow handling', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // First item has 3 tags, should show 2 + overflow
      const reactRow = screen.getByText('react.dev').closest('tr')
      const tagCell = within(reactRow!).getByText('react').closest('td')
      
      expect(within(tagCell!).getByText('react')).toBeInTheDocument()
      expect(within(tagCell!).getByText('frontend')).toBeInTheDocument()
      expect(within(tagCell!).getByText('+1')).toBeInTheDocument()
    })

    it('should display chunk counts', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // Grouped items should sum chunks
      const reactRow = screen.getByText('react.dev').closest('tr')
      expect(within(reactRow!).getByText('75')).toBeInTheDocument() // 45 + 30

      // Single item shows its chunk count
      const fileRow = screen.getByText('System Design Concepts').closest('tr')
      expect(within(fileRow!).getByText('120')).toBeInTheDocument()
    })

    it('should format dates correctly', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // Check date formatting
      expect(screen.getByText('Jan 03, 2024')).toBeInTheDocument()
      expect(screen.getByText('Jan 04, 2024')).toBeInTheDocument()
    })
  })

  describe('Update Frequency Display', () => {
    test.each([
      { frequency: 0, expectedText: 'Never', expectedIcon: 'x-icon' },
      { frequency: 1, expectedText: 'Daily', expectedIcon: 'refresh-icon' },
      { frequency: 7, expectedText: 'Weekly', expectedIcon: 'refresh-icon' },
      { frequency: 30, expectedText: 'Monthly', expectedIcon: 'refresh-icon' }
    ])('should display $expectedText for frequency $frequency', ({ frequency, expectedText, expectedIcon }) => {
      const item: KnowledgeItem = {
        ...mockKnowledgeItems[0],
        metadata: { ...mockKnowledgeItems[0].metadata, update_frequency: frequency }
      }
      
      render(<KnowledgeTable items={[item]} onDelete={mockOnDelete} />)
      
      expect(screen.getByText(expectedText)).toBeInTheDocument()
      expect(screen.getByTestId(expectedIcon)).toBeInTheDocument()
    })

    it('should display custom frequency for non-standard values', () => {
      const item: KnowledgeItem = {
        ...mockKnowledgeItems[0],
        metadata: { ...mockKnowledgeItems[0].metadata, update_frequency: 14 }
      }
      
      render(<KnowledgeTable items={[item]} onDelete={mockOnDelete} />)
      
      expect(screen.getByText('Every 14 days')).toBeInTheDocument()
    })
  })

  describe('Status Display', () => {
    it('should display status badges with correct colors', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // Active status
      const activeBadge = screen.getByText('Active')
      expect(activeBadge.parentElement).toHaveClass('bg-green-100')

      // Processing status
      const processingBadge = screen.getByText('Processing')
      expect(processingBadge.parentElement).toHaveClass('bg-blue-100')

      // Error status
      const errorBadge = screen.getByText('Error')
      expect(errorBadge.parentElement).toHaveClass('bg-pink-100')
    })
  })

  describe('Grouped Items Tooltip', () => {
    it('should show tooltip on hover for grouped items', async () => {
      const user = userEvent.setup()
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // Find grouped badge
      const groupedBadge = screen.getByText('2').parentElement
      
      // Hover to show tooltip
      await user.hover(groupedBadge!)
      
      // Check tooltip content
      expect(screen.getByText('Grouped Sources:')).toBeInTheDocument()
      expect(screen.getByText('1. source-1')).toBeInTheDocument()
      expect(screen.getByText('2. source-2')).toBeInTheDocument()
    })
  })

  describe('Delete Functionality', () => {
    it('should delete single entries', async () => {
      const user = userEvent.setup()
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // Find delete button for file upload (not grouped)
      const fileRow = screen.getByText('System Design Concepts').closest('tr')
      const deleteButton = within(fileRow!).getByTestId('trash-icon').parentElement
      
      await user.click(deleteButton!)
      
      expect(mockOnDelete).toHaveBeenCalledWith('source-3')
      expect(mockOnDelete).toHaveBeenCalledTimes(1)
    })

    it('should delete all items in a group', async () => {
      const user = userEvent.setup()
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      // Find delete button for grouped items
      const groupedRow = screen.getByText('react.dev').closest('tr')
      const deleteButton = within(groupedRow!).getByTestId('trash-icon').parentElement
      
      await user.click(deleteButton!)
      
      // Should delete both items in the group
      expect(mockOnDelete).toHaveBeenCalledWith('source-1')
      expect(mockOnDelete).toHaveBeenCalledWith('source-2')
      expect(mockOnDelete).toHaveBeenCalledTimes(2)
    })

    it('should show appropriate delete title for grouped items', async () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      const groupedRow = screen.getByText('react.dev').closest('tr')
      const deleteButton = within(groupedRow!).getByTestId('trash-icon').parentElement
      
      expect(deleteButton).toHaveAttribute('title', 'Delete 2 sources')
    })
  })

  describe('Empty State', () => {
    it('should render empty table when no items', () => {
      render(<KnowledgeTable items={[]} onDelete={mockOnDelete} />)

      expect(screen.getByRole('table')).toBeInTheDocument()
      const tbody = screen.getByRole('table').querySelector('tbody')
      expect(tbody?.children).toHaveLength(0)
    })
  })

  describe('Row Styling', () => {
    it('should apply hover styles to rows', () => {
      render(<KnowledgeTable items={mockKnowledgeItems} onDelete={mockOnDelete} />)

      const rows = screen.getAllByRole('row').filter(row => row.parentElement?.tagName === 'TBODY')
      rows.forEach(row => {
        expect(row).toHaveClass('hover:bg-gray-50')
      })
    })
  })
})