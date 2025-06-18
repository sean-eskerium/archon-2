import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Toggle } from '@/components/ui/Toggle'

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

describe('Toggle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Basic Functionality', () => {
    it('should toggle on click', async () => {
      const user = userEvent.setup()
      const handleChange = vi.fn()
      
      render(<Toggle checked={false} onCheckedChange={handleChange} />)
      
      const toggle = screen.getByRole('switch')
      await user.click(toggle)
      
      expect(handleChange).toHaveBeenCalledWith(true)
    })

    it('should show checked state', () => {
      render(<Toggle checked={true} onCheckedChange={() => {}} />)
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveAttribute('aria-checked', 'true')
      expect(toggle).toHaveClass('toggle-checked')
    })

    it('should show unchecked state', () => {
      render(<Toggle checked={false} onCheckedChange={() => {}} />)
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveAttribute('aria-checked', 'false')
      expect(toggle).not.toHaveClass('toggle-checked')
    })

    it('should be disabled when specified', () => {
      render(<Toggle checked={false} onCheckedChange={() => {}} disabled />)
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toBeDisabled()
      expect(toggle).toHaveClass('toggle-disabled')
    })

    it('should not trigger onChange when disabled', async () => {
      const user = userEvent.setup()
      const handleChange = vi.fn()
      
      render(<Toggle checked={false} onCheckedChange={handleChange} disabled />)
      
      const toggle = screen.getByRole('switch')
      await user.click(toggle)
      
      expect(handleChange).not.toHaveBeenCalled()
    })
  })

  describe('Accent Colors', () => {
    it('should apply blue accent color by default', () => {
      render(<Toggle checked={false} onCheckedChange={() => {}} />)
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveClass('toggle-blue')
    })

    it('should apply purple accent color', () => {
      render(<Toggle checked={false} onCheckedChange={() => {}} accentColor="purple" />)
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveClass('toggle-purple')
    })

    it('should apply green accent color', () => {
      render(<Toggle checked={false} onCheckedChange={() => {}} accentColor="green" />)
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveClass('toggle-green')
    })

    it('should apply pink accent color', () => {
      render(<Toggle checked={false} onCheckedChange={() => {}} accentColor="pink" />)
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveClass('toggle-pink')
    })

    it('should apply orange accent color', () => {
      render(<Toggle checked={false} onCheckedChange={() => {}} accentColor="orange" />)
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveClass('toggle-orange')
    })
  })

  describe('Icon Support', () => {
    it('should render icon when provided', () => {
      const TestIcon = () => <svg data-testid="test-icon">Icon</svg>
      
      render(
        <Toggle 
          checked={false} 
          onCheckedChange={() => {}} 
          icon={<TestIcon />}
        />
      )
      
      expect(screen.getByTestId('test-icon')).toBeInTheDocument()
      const iconWrapper = screen.getByTestId('test-icon').parentElement
      expect(iconWrapper).toHaveClass('toggle-icon')
    })

    it('should not render icon wrapper when no icon provided', () => {
      render(<Toggle checked={false} onCheckedChange={() => {}} />)
      
      const iconWrapper = screen.getByRole('switch').querySelector('.toggle-icon')
      expect(iconWrapper).not.toBeInTheDocument()
    })
  })

  describe('Toggle Behavior', () => {
    it('should toggle from unchecked to checked', async () => {
      const user = userEvent.setup()
      const handleChange = vi.fn()
      
      render(<Toggle checked={false} onCheckedChange={handleChange} />)
      
      await user.click(screen.getByRole('switch'))
      
      expect(handleChange).toHaveBeenCalledWith(true)
      expect(handleChange).toHaveBeenCalledOnce()
    })

    it('should toggle from checked to unchecked', async () => {
      const user = userEvent.setup()
      const handleChange = vi.fn()
      
      render(<Toggle checked={true} onCheckedChange={handleChange} />)
      
      await user.click(screen.getByRole('switch'))
      
      expect(handleChange).toHaveBeenCalledWith(false)
      expect(handleChange).toHaveBeenCalledOnce()
    })

    it('should handle rapid clicks', async () => {
      const user = userEvent.setup()
      const handleChange = vi.fn()
      
      render(<Toggle checked={false} onCheckedChange={handleChange} />)
      
      const toggle = screen.getByRole('switch')
      await user.click(toggle)
      await user.click(toggle)
      await user.click(toggle)
      
      expect(handleChange).toHaveBeenCalledTimes(3)
      expect(handleChange).toHaveBeenNthCalledWith(1, true)
      expect(handleChange).toHaveBeenNthCalledWith(2, true)
      expect(handleChange).toHaveBeenNthCalledWith(3, true)
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      render(<Toggle checked={true} onCheckedChange={() => {}} />)
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveAttribute('role', 'switch')
      expect(toggle).toHaveAttribute('aria-checked', 'true')
    })

    it('should be keyboard accessible', async () => {
      const user = userEvent.setup()
      const handleChange = vi.fn()
      
      render(<Toggle checked={false} onCheckedChange={handleChange} />)
      
      // Tab to focus the toggle
      await user.tab()
      expect(screen.getByRole('switch')).toHaveFocus()
      
      // Space or Enter should activate
      await user.keyboard(' ')
      expect(handleChange).toHaveBeenCalledWith(true)
    })
  })

  describe('Styling', () => {
    it('should have base toggle classes', () => {
      render(<Toggle checked={false} onCheckedChange={() => {}} />)
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveClass('toggle-switch')
    })

    it('should have toggle thumb element', () => {
      render(<Toggle checked={false} onCheckedChange={() => {}} />)
      
      const thumb = screen.getByRole('switch').querySelector('.toggle-thumb')
      expect(thumb).toBeInTheDocument()
    })

    it('should apply multiple state classes correctly', () => {
      render(
        <Toggle 
          checked={true} 
          onCheckedChange={() => {}} 
          disabled 
          accentColor="purple"
        />
      )
      
      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveClass('toggle-switch')
      expect(toggle).toHaveClass('toggle-checked')
      expect(toggle).toHaveClass('toggle-disabled')
      expect(toggle).toHaveClass('toggle-purple')
    })
  })
})