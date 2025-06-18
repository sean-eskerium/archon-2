import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { ThemeProvider } from '@/contexts/ThemeContext'

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Sun: ({ className }: { className?: string }) => <div data-testid="sun-icon" className={className}>Sun</div>,
  Moon: ({ className }: { className?: string }) => <div data-testid="moon-icon" className={className}>Moon</div>
}))

// Mock ThemeContext
const mockSetTheme = vi.fn()
const mockTheme = vi.fn()

vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: mockTheme(),
    setTheme: mockSetTheme
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>
}))

describe('ThemeToggle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockTheme.mockReturnValue('light') // Default to light theme
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Basic Functionality', () => {
    it('should toggle theme on click', async () => {
      const user = userEvent.setup()
      render(<ThemeToggle />)
      
      const button = screen.getByRole('button')
      await user.click(button)
      
      expect(mockSetTheme).toHaveBeenCalledWith('dark')
    })

    it('should toggle from dark to light', async () => {
      const user = userEvent.setup()
      mockTheme.mockReturnValue('dark')
      
      render(<ThemeToggle />)
      
      const button = screen.getByRole('button')
      await user.click(button)
      
      expect(mockSetTheme).toHaveBeenCalledWith('light')
    })
  })

  describe('Theme Display', () => {
    it('should show moon icon in light theme', () => {
      mockTheme.mockReturnValue('light')
      render(<ThemeToggle />)
      
      expect(screen.getByTestId('moon-icon')).toBeInTheDocument()
      expect(screen.queryByTestId('sun-icon')).not.toBeInTheDocument()
    })

    it('should show sun icon in dark theme', () => {
      mockTheme.mockReturnValue('dark')
      render(<ThemeToggle />)
      
      expect(screen.getByTestId('sun-icon')).toBeInTheDocument()
      expect(screen.queryByTestId('moon-icon')).not.toBeInTheDocument()
    })

    it('should have appropriate icon size', () => {
      render(<ThemeToggle />)
      
      const icon = screen.getByTestId('moon-icon')
      expect(icon).toHaveClass('w-5', 'h-5')
    })
  })

  describe('Accessibility', () => {
    it('should have proper aria-label in light theme', () => {
      mockTheme.mockReturnValue('light')
      render(<ThemeToggle />)
      
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-label', 'Switch to dark mode')
    })

    it('should have proper aria-label in dark theme', () => {
      mockTheme.mockReturnValue('dark')
      render(<ThemeToggle />)
      
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-label', 'Switch to light mode')
    })

    it('should be keyboard accessible', async () => {
      const user = userEvent.setup()
      render(<ThemeToggle />)
      
      // Tab to focus the button
      await user.tab()
      expect(screen.getByRole('button')).toHaveFocus()
      
      // Space or Enter should activate
      await user.keyboard(' ')
      expect(mockSetTheme).toHaveBeenCalledWith('dark')
    })
  })

  describe('Accent Colors', () => {
    it('should apply blue accent color by default', () => {
      render(<ThemeToggle />)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('border-blue-300')
      expect(button).toHaveClass('hover:border-blue-400')
      expect(button).toHaveClass('text-blue-600')
      expect(button).toHaveClass('from-blue-100/80', 'to-blue-50/60')
    })

    it('should apply purple accent color', () => {
      render(<ThemeToggle accentColor="purple" />)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('border-purple-300')
      expect(button).toHaveClass('hover:border-purple-400')
      expect(button).toHaveClass('text-purple-600')
    })

    it('should apply green accent color', () => {
      render(<ThemeToggle accentColor="green" />)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('border-emerald-300')
      expect(button).toHaveClass('hover:border-emerald-400')
      expect(button).toHaveClass('text-emerald-600')
    })

    it('should apply pink accent color', () => {
      render(<ThemeToggle accentColor="pink" />)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('border-pink-300')
      expect(button).toHaveClass('hover:border-pink-400')
      expect(button).toHaveClass('text-pink-600')
    })
  })

  describe('Styling', () => {
    it('should apply base button styles', () => {
      render(<ThemeToggle />)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('relative', 'p-2', 'rounded-md', 'backdrop-blur-md')
      expect(button).toHaveClass('bg-gradient-to-b')
      expect(button).toHaveClass('transition-all', 'duration-300')
      expect(button).toHaveClass('flex', 'items-center', 'justify-center')
    })

    it('should have shadow effects', () => {
      render(<ThemeToggle />)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('shadow-[0_0_10px_rgba(0,0,0,0.05)]')
    })
  })

  describe('Theme Integration', () => {
    it('should work with ThemeProvider wrapper', () => {
      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      )
      
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('should handle rapid theme toggles', async () => {
      const user = userEvent.setup()
      render(<ThemeToggle />)
      
      const button = screen.getByRole('button')
      
      // Click multiple times rapidly
      await user.click(button)
      await user.click(button)
      await user.click(button)
      
      expect(mockSetTheme).toHaveBeenCalledTimes(3)
      expect(mockSetTheme).toHaveBeenNthCalledWith(1, 'dark')
      expect(mockSetTheme).toHaveBeenNthCalledWith(2, 'dark')
      expect(mockSetTheme).toHaveBeenNthCalledWith(3, 'dark')
    })
  })
})