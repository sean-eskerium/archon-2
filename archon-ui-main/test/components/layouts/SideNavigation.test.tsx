import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SideNavigation } from '@/components/layouts/SideNavigation'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

// Mock dependencies
vi.mock('@/contexts/SettingsContext', () => ({
  useSettings: vi.fn(() => ({
    projectsEnabled: true
  }))
}))

// Mock Lucide icons
vi.mock('lucide-react', () => ({
  BookOpen: ({ className }: any) => <span className={className} data-testid="book-open-icon">BookOpen</span>,
  HardDrive: ({ className }: any) => <span className={className} data-testid="hard-drive-icon">HardDrive</span>,
  Settings: ({ className }: any) => <span className={className} data-testid="settings-icon">Settings</span>
}))

describe('SideNavigation', () => {
  const renderWithRouter = (component: React.ReactNode, initialRoute = '/') => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="*" element={component} />
        </Routes>
      </MemoryRouter>
    )
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Navigation Items', () => {
    it('should render all navigation items correctly', () => {
      renderWithRouter(<SideNavigation />)

      // Verify all navigation links
      expect(screen.getByRole('link', { name: 'Knowledge Base' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'MCP Server' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Settings' })).toBeInTheDocument()

      // Verify icons
      expect(screen.getByTestId('book-open-icon')).toBeInTheDocument()
      expect(screen.getByTestId('hard-drive-icon')).toBeInTheDocument()
      expect(screen.getByTestId('settings-icon')).toBeInTheDocument()
    })

    it('should render logo with correct attributes', () => {
      renderWithRouter(<SideNavigation />)

      const logo = screen.getByAltText('Knowledge Base Logo')
      expect(logo).toBeInTheDocument()
      expect(logo).toHaveAttribute('src', '/logo-neon.svg')
      expect(logo).toHaveClass('w-8', 'h-8')
    })

    it('should apply custom className prop', () => {
      renderWithRouter(<SideNavigation className="custom-class" />)

      const nav = document.querySelector('.custom-class')
      expect(nav).toBeInTheDocument()
    })

    it('should apply data-id prop', () => {
      renderWithRouter(<SideNavigation data-id="test-navigation" />)

      const nav = document.querySelector('[data-id="test-navigation"]')
      expect(nav).toBeInTheDocument()
    })
  })

  describe('Active Route Highlighting', () => {
    test.each([
      { route: '/', expectedActive: 'Knowledge Base' },
      { route: '/mcp', expectedActive: 'MCP Server' },
      { route: '/settings', expectedActive: 'Settings' },
      { route: '/projects', expectedActive: 'logo' }
    ])('should highlight $expectedActive when route is $route', ({ route, expectedActive }) => {
      renderWithRouter(<SideNavigation />, route)

      if (expectedActive === 'logo') {
        // For projects route, check logo active state
        const logo = screen.getByAltText('Knowledge Base Logo').parentElement
        expect(logo).toHaveClass('transform', 'scale-110')
        expect(logo?.querySelector('.border-blue-300')).toBeInTheDocument()
      } else {
        // For other routes, check nav item active state
        const activeLink = screen.getByRole('link', { name: expectedActive })
        expect(activeLink).toHaveClass('text-blue-600', 'dark:text-blue-400')
        expect(activeLink.querySelector('.border-blue-300')).toBeInTheDocument()
        expect(activeLink.querySelector('.bg-blue-500')).toBeInTheDocument() // Neon line
      }
    })
  })

  describe('Navigation Behavior', () => {
    it('should navigate when items are clicked', async () => {
      const user = userEvent.setup()
      let currentPath = '/'
      
      renderWithRouter(
        <>
          <SideNavigation />
          <Routes>
            <Route path="/" element={<div>Knowledge Base Page</div>} />
            <Route path="/mcp" element={<div>MCP Page</div>} />
            <Route path="/settings" element={<div>Settings Page</div>} />
          </Routes>
        </>,
        currentPath
      )

      // Click MCP Server link
      await user.click(screen.getByRole('link', { name: 'MCP Server' }))
      expect(screen.getByText('MCP Page')).toBeInTheDocument()

      // Click Settings link
      await user.click(screen.getByRole('link', { name: 'Settings' }))
      expect(screen.getByText('Settings Page')).toBeInTheDocument()
    })

    it('should navigate to projects when logo is clicked', async () => {
      const user = userEvent.setup()
      
      renderWithRouter(
        <>
          <SideNavigation />
          <Routes>
            <Route path="/" element={<div>Home</div>} />
            <Route path="/projects" element={<div>Projects Page</div>} />
          </Routes>
        </>
      )

      // Click logo
      const logoLink = screen.getByAltText('Knowledge Base Logo').parentElement as HTMLElement
      await user.click(logoLink)
      
      expect(screen.getByText('Projects Page')).toBeInTheDocument()
    })
  })

  describe('Feature Flag Integration', () => {
    it('should disable projects navigation when projects feature is disabled', async () => {
      const { useSettings } = await import('@/contexts/SettingsContext')
      vi.mocked(useSettings).mockReturnValueOnce({
        projectsEnabled: false
      } as any)

      renderWithRouter(<SideNavigation />)

      const logoContainer = screen.getByAltText('Knowledge Base Logo').parentElement
      
      // Logo should not be a link
      expect(logoContainer?.tagName).not.toBe('A')
      
      // Logo should have disabled styling
      expect(logoContainer).toHaveClass('opacity-50', 'cursor-not-allowed')
    })

    it('should enable projects navigation when projects feature is enabled', () => {
      renderWithRouter(<SideNavigation />)

      const logoContainer = screen.getByAltText('Knowledge Base Logo').parentElement
      
      // Logo should be a link
      expect(logoContainer?.tagName).toBe('A')
      expect(logoContainer).toHaveAttribute('href', '/projects')
      
      // Logo should have enabled styling
      expect(logoContainer).toHaveClass('hover:bg-white/10', 'cursor-pointer')
      expect(logoContainer).not.toHaveClass('opacity-50', 'cursor-not-allowed')
    })
  })

  describe('Tooltip Behavior', () => {
    it('should show tooltip on hover for navigation items', async () => {
      const user = userEvent.setup()
      renderWithRouter(<SideNavigation />)

      // Hover over Knowledge Base
      const knowledgeLink = screen.getByRole('link', { name: 'Knowledge Base' })
      await user.hover(knowledgeLink)
      
      // Tooltip should appear
      expect(screen.getByText('Knowledge Base', { selector: '.text-xs' })).toBeInTheDocument()

      // Unhover
      await user.unhover(knowledgeLink)
      
      // Tooltip should disappear
      expect(screen.queryByText('Knowledge Base', { selector: '.text-xs' })).not.toBeInTheDocument()
    })

    it('should show appropriate tooltip for logo based on projects state', async () => {
      const user = userEvent.setup()
      renderWithRouter(<SideNavigation />)

      // Hover over logo when projects enabled
      const logo = screen.getByAltText('Knowledge Base Logo')
      await user.hover(logo)
      
      expect(screen.getByText('Project Management')).toBeInTheDocument()
    })

    it('should show disabled tooltip when projects feature is off', async () => {
      const { useSettings } = await import('@/contexts/SettingsContext')
      vi.mocked(useSettings).mockReturnValueOnce({
        projectsEnabled: false
      } as any)

      const user = userEvent.setup()
      renderWithRouter(<SideNavigation />)

      // Hover over logo
      const logo = screen.getByAltText('Knowledge Base Logo')
      await user.hover(logo)
      
      expect(screen.getByText('Projects Disabled')).toBeInTheDocument()
    })
  })

  describe('Visual Styling', () => {
    it('should have proper container styling', () => {
      renderWithRouter(<SideNavigation />)

      const container = screen.getByRole('link', { name: 'Knowledge Base' }).closest('.flex.flex-col')
      expect(container).toHaveClass(
        'flex',
        'flex-col',
        'items-center',
        'gap-6',
        'py-6',
        'px-3',
        'rounded-xl',
        'backdrop-blur-md'
      )
    })

    it('should apply hover effects to navigation items', async () => {
      const user = userEvent.setup()
      renderWithRouter(<SideNavigation />)

      const mcpLink = screen.getByRole('link', { name: 'MCP Server' })
      
      // Initial state (not active)
      expect(mcpLink).toHaveClass('text-gray-500', 'hover:text-blue-600')

      // Can't directly test hover state changes in RTL, but we verify the classes exist
      expect(mcpLink.className).toContain('hover:text-blue-600')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels on navigation links', () => {
      renderWithRouter(<SideNavigation />)

      expect(screen.getByRole('link', { name: 'Knowledge Base' })).toHaveAttribute('aria-label', 'Knowledge Base')
      expect(screen.getByRole('link', { name: 'MCP Server' })).toHaveAttribute('aria-label', 'MCP Server')
      expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('aria-label', 'Settings')
    })

    it('should be keyboard navigable', async () => {
      const user = userEvent.setup()
      renderWithRouter(<SideNavigation />)

      // Tab through navigation items
      await user.tab()
      expect(screen.getByAltText('Knowledge Base Logo').parentElement).toHaveFocus()

      await user.tab()
      expect(screen.getByRole('link', { name: 'Knowledge Base' })).toHaveFocus()

      await user.tab()
      expect(screen.getByRole('link', { name: 'MCP Server' })).toHaveFocus()

      await user.tab()
      expect(screen.getByRole('link', { name: 'Settings' })).toHaveFocus()
    })
  })
})