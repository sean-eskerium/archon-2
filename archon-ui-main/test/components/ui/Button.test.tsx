import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from '@/components/ui/Button'

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

describe('Button', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Basic Functionality', () => {
    it('should render with text', () => {
      render(<Button>Click me</Button>)
      
      expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
    })

    it('should handle click events', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()
      
      render(<Button onClick={handleClick}>Click me</Button>)
      
      await user.click(screen.getByRole('button'))
      
      expect(handleClick).toHaveBeenCalledOnce()
    })

    it('should be disabled when specified', () => {
      render(<Button disabled>Disabled button</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('should forward HTML button attributes', () => {
      render(
        <Button 
          type="submit" 
          name="submitBtn"
          value="submitValue"
          form="testForm"
        >
          Submit
        </Button>
      )
      
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('type', 'submit')
      expect(button).toHaveAttribute('name', 'submitBtn')
      expect(button).toHaveAttribute('value', 'submitValue')
      expect(button).toHaveAttribute('form', 'testForm')
    })
  })

  describe('Variants', () => {
    it('should apply primary variant styles', () => {
      render(<Button variant="primary">Primary</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-purple-500/80', 'text-black', 'shadow-lg')
    })

    it('should apply secondary variant styles', () => {
      render(<Button variant="secondary">Secondary</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-black/90', 'border-purple-500', 'text-purple-400')
    })

    it('should apply outline variant styles', () => {
      render(<Button variant="outline">Outline</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-white', 'border-purple-500', 'hover:bg-purple-500/10')
    })

    it('should apply ghost variant styles', () => {
      render(<Button variant="ghost">Ghost</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-transparent', 'hover:bg-gray-100/50')
    })
  })

  describe('Sizes', () => {
    it('should apply small size styles', () => {
      render(<Button size="sm">Small</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('text-xs', 'px-3', 'py-1.5', 'rounded')
    })

    it('should apply medium size styles by default', () => {
      render(<Button>Medium</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('text-sm', 'px-4', 'py-2', 'rounded-md')
    })

    it('should apply large size styles', () => {
      render(<Button size="lg">Large</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('text-base', 'px-6', 'py-2.5', 'rounded-md')
    })
  })

  describe('Accent Colors', () => {
    it('should apply purple accent color by default', () => {
      render(<Button variant="primary">Purple</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-purple-500/80')
    })

    it('should apply green accent color', () => {
      render(<Button variant="primary" accentColor="green">Green</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-green-500/80')
    })

    it('should apply pink accent color', () => {
      render(<Button variant="primary" accentColor="pink">Pink</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-pink-500/80')
    })

    it('should apply blue accent color', () => {
      render(<Button variant="primary" accentColor="blue">Blue</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-blue-500/80')
    })

    it('should apply cyan accent color', () => {
      render(<Button variant="primary" accentColor="cyan">Cyan</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-cyan-500/80')
    })

    it('should apply orange accent color', () => {
      render(<Button variant="primary" accentColor="orange">Orange</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-orange-500/80')
    })
  })

  describe('Icon Support', () => {
    it('should support icons', () => {
      const TestIcon = () => <svg data-testid="test-icon">Icon</svg>
      
      render(
        <Button icon={<TestIcon />}>
          Button with icon
        </Button>
      )
      
      expect(screen.getByTestId('test-icon')).toBeInTheDocument()
      expect(screen.getByText('Button with icon')).toBeInTheDocument()
      
      // Check icon spacing
      const iconWrapper = screen.getByTestId('test-icon').parentElement
      expect(iconWrapper).toHaveClass('mr-2')
    })

    it('should render icon before text', () => {
      const TestIcon = () => <span data-testid="test-icon">🎨</span>
      
      render(
        <Button icon={<TestIcon />}>
          Button text
        </Button>
      )
      
      const button = screen.getByRole('button')
      const buttonContent = button.textContent
      
      // Icon should come before text
      expect(buttonContent).toBe('🎨Button text')
    })
  })

  describe('Neon Line', () => {
    it('should show neon line when enabled', () => {
      render(<Button neonLine>Neon button</Button>)
      
      const button = screen.getByRole('button')
      const neonLine = button.querySelector('.absolute.bottom-0')
      
      expect(neonLine).toBeInTheDocument()
      expect(neonLine).toHaveClass('bg-purple-500')
      expect(neonLine).toHaveClass('shadow-[0_0_10px_2px_rgba(168,85,247,0.4)]')
    })

    it('should not show neon line by default', () => {
      render(<Button>No neon</Button>)
      
      const button = screen.getByRole('button')
      const neonLine = button.querySelector('.absolute.bottom-0')
      
      expect(neonLine).not.toBeInTheDocument()
    })

    it('should apply correct neon color based on accent', () => {
      render(<Button neonLine accentColor="cyan">Cyan neon</Button>)
      
      const button = screen.getByRole('button')
      const neonLine = button.querySelector('.absolute.bottom-0')
      
      expect(neonLine).toHaveClass('bg-cyan-500')
      expect(neonLine).toHaveClass('shadow-[0_0_10px_2px_rgba(34,211,238,0.4)]')
    })
  })

  describe('Custom Styling', () => {
    it('should accept custom className', () => {
      render(<Button className="custom-class">Custom</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('custom-class')
    })

    it('should merge custom className with default styles', () => {
      render(<Button className="mt-4" size="sm">Custom margin</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('mt-4')
      expect(button).toHaveClass('text-xs') // Should still have size styles
    })
  })

  describe('Primary Variant Effects', () => {
    it('should render glow effects for primary variant', () => {
      render(<Button variant="primary">Glowing</Button>)
      
      const button = screen.getByRole('button')
      
      // Should have luminous glow div
      const glowDiv = button.querySelector('.luminous-button-glow')
      expect(glowDiv).toBeInTheDocument()
      
      // Should have shine effect
      const shineDiv = button.querySelector('.bg-white\\/70')
      expect(shineDiv).toBeInTheDocument()
    })

    it('should not render glow effects for non-primary variants', () => {
      render(<Button variant="outline">No glow</Button>)
      
      const button = screen.getByRole('button')
      const glowDiv = button.querySelector('.luminous-button-glow')
      
      expect(glowDiv).not.toBeInTheDocument()
    })
  })
})