import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/project-tasks/Tabs'

// Mock dependencies
vi.mock('@/services/websocketService', () => ({
  websocketService: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    send: vi.fn(),
  }
}))

describe('Tabs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Tab Rendering', () => {
    it('should render all tabs', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
            <TabsTrigger value="tab2">Tab 2</TabsTrigger>
            <TabsTrigger value="tab3">Tab 3</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content 1</TabsContent>
          <TabsContent value="tab2">Content 2</TabsContent>
          <TabsContent value="tab3">Content 3</TabsContent>
        </Tabs>
      )

      expect(screen.getByText('Tab 1')).toBeInTheDocument()
      expect(screen.getByText('Tab 2')).toBeInTheDocument()
      expect(screen.getByText('Tab 3')).toBeInTheDocument()
    })

    it('should show default tab content', () => {
      render(
        <Tabs defaultValue="tab2">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
            <TabsTrigger value="tab2">Tab 2</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content 1</TabsContent>
          <TabsContent value="tab2">Content 2</TabsContent>
        </Tabs>
      )

      expect(screen.getByText('Content 2')).toBeInTheDocument()
      expect(screen.queryByText('Content 1')).not.toBeInTheDocument()
    })

    it('should apply custom className to Tabs container', () => {
      render(
        <Tabs defaultValue="tab1" className="custom-tabs">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content 1</TabsContent>
        </Tabs>
      )

      const container = screen.getByText('Tab 1').closest('.custom-tabs')
      expect(container).toBeInTheDocument()
    })
  })

  describe('Tab Switching', () => {
    it('should switch between tabs when clicked', async () => {
      const user = userEvent.setup()
      
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
            <TabsTrigger value="tab2">Tab 2</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content 1</TabsContent>
          <TabsContent value="tab2">Content 2</TabsContent>
        </Tabs>
      )

      // Initially tab1 is active
      expect(screen.getByText('Content 1')).toBeInTheDocument()
      expect(screen.queryByText('Content 2')).not.toBeInTheDocument()

      // Click tab2
      await user.click(screen.getByText('Tab 2'))

      // Now tab2 should be active
      expect(screen.queryByText('Content 1')).not.toBeInTheDocument()
      expect(screen.getByText('Content 2')).toBeInTheDocument()
    })

    it('should call onValueChange when tab changes', async () => {
      const user = userEvent.setup()
      const onValueChange = vi.fn()
      
      render(
        <Tabs defaultValue="tab1" onValueChange={onValueChange}>
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
            <TabsTrigger value="tab2">Tab 2</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content 1</TabsContent>
          <TabsContent value="tab2">Content 2</TabsContent>
        </Tabs>
      )

      await user.click(screen.getByText('Tab 2'))

      expect(onValueChange).toHaveBeenCalledWith('tab2')
    })

    it('should call custom onClick handler on TabsTrigger', async () => {
      const user = userEvent.setup()
      const onClick = vi.fn()
      
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1" onClick={onClick}>Tab 1</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content 1</TabsContent>
        </Tabs>
      )

      await user.click(screen.getByText('Tab 1'))

      expect(onClick).toHaveBeenCalled()
    })
  })

  describe('Controlled vs Uncontrolled', () => {
    it('should work as controlled component', async () => {
      const user = userEvent.setup()
      let activeTab = 'tab1'
      
      const { rerender } = render(
        <Tabs value={activeTab} onValueChange={(value) => { activeTab = value }}>
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
            <TabsTrigger value="tab2">Tab 2</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content 1</TabsContent>
          <TabsContent value="tab2">Content 2</TabsContent>
        </Tabs>
      )

      expect(screen.getByText('Content 1')).toBeInTheDocument()

      // Click tab2
      await user.click(screen.getByText('Tab 2'))

      // Rerender with new value
      rerender(
        <Tabs value={activeTab} onValueChange={(value) => { activeTab = value }}>
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
            <TabsTrigger value="tab2">Tab 2</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content 1</TabsContent>
          <TabsContent value="tab2">Content 2</TabsContent>
        </Tabs>
      )

      expect(screen.getByText('Content 2')).toBeInTheDocument()
    })

    it('should maintain internal state when uncontrolled', async () => {
      const user = userEvent.setup()
      
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
            <TabsTrigger value="tab2">Tab 2</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content 1</TabsContent>
          <TabsContent value="tab2">Content 2</TabsContent>
        </Tabs>
      )

      // Switch to tab2
      await user.click(screen.getByText('Tab 2'))
      expect(screen.getByText('Content 2')).toBeInTheDocument()

      // Switch back to tab1
      await user.click(screen.getByText('Tab 1'))
      expect(screen.getByText('Content 1')).toBeInTheDocument()
    })
  })

  describe('TabsTrigger Styling', () => {
    it('should apply active state styling', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
            <TabsTrigger value="tab2">Tab 2</TabsTrigger>
          </TabsList>
        </Tabs>
      )

      const activeTab = screen.getByRole('tab', { selected: true })
      const inactiveTab = screen.getByRole('tab', { selected: false })

      expect(activeTab).toHaveAttribute('aria-selected', 'true')
      expect(activeTab).toHaveAttribute('data-state', 'active')
      expect(inactiveTab).toHaveAttribute('aria-selected', 'false')
      expect(inactiveTab).toHaveAttribute('data-state', 'inactive')
    })

    it('should apply color variants', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1" color="blue">Blue Tab</TabsTrigger>
            <TabsTrigger value="tab2" color="purple">Purple Tab</TabsTrigger>
            <TabsTrigger value="tab3" color="pink">Pink Tab</TabsTrigger>
            <TabsTrigger value="tab4" color="cyan">Cyan Tab</TabsTrigger>
          </TabsList>
        </Tabs>
      )

      const blueTab = screen.getByText('Blue Tab')
      expect(blueTab).toHaveClass('text-blue-600')

      // Active indicator should have appropriate color
      const activeIndicator = blueTab.querySelector('.bg-blue-500')
      expect(activeIndicator).toBeInTheDocument()
    })

    it('should show neon glow effect on active tab', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1" color="cyan">Tab 1</TabsTrigger>
          </TabsList>
        </Tabs>
      )

      const activeTab = screen.getByRole('tab', { selected: true })
      const glowIndicator = activeTab.querySelector('.shadow-\\[0_0_10px_2px_rgba\\(34\\,211\\,238\\,0\\.4\\)\\]')
      expect(glowIndicator).toBeInTheDocument()
    })
  })

  describe('TabsContent Behavior', () => {
    it('should only render active tab content', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
            <TabsTrigger value="tab2">Tab 2</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">
            <div data-testid="content-1">Content 1</div>
          </TabsContent>
          <TabsContent value="tab2">
            <div data-testid="content-2">Content 2</div>
          </TabsContent>
        </Tabs>
      )

      expect(screen.getByTestId('content-1')).toBeInTheDocument()
      expect(screen.queryByTestId('content-2')).not.toBeInTheDocument()
    })

    it('should apply custom className to TabsContent', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1" className="custom-content">
            Content 1
          </TabsContent>
        </Tabs>
      )

      const content = screen.getByRole('tabpanel')
      expect(content).toHaveClass('custom-content')
    })

    it('should have correct aria attributes on content', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          </TabsList>
          <TabsContent value="tab1">Content 1</TabsContent>
        </Tabs>
      )

      const panel = screen.getByRole('tabpanel')
      expect(panel).toHaveAttribute('data-state', 'active')
    })
  })

  describe('TabsList Behavior', () => {
    it('should render with tablist role', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          </TabsList>
        </Tabs>
      )

      expect(screen.getByRole('tablist')).toBeInTheDocument()
    })

    it('should apply custom className to TabsList', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList className="custom-list">
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          </TabsList>
        </Tabs>
      )

      const list = screen.getByRole('tablist')
      expect(list).toHaveClass('custom-list')
    })

    it('should have glow effect background', () => {
      render(
        <Tabs defaultValue="tab1">
          <TabsList>
            <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          </TabsList>
        </Tabs>
      )

      const list = screen.getByRole('tablist')
      const glowElement = list.querySelector('.bg-gradient-to-r')
      expect(glowElement).toBeInTheDocument()
      expect(glowElement).toHaveClass('blur-\\[1px\\]')
    })
  })
})