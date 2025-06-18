import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Card } from '@/components/ui/Card'

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

describe('Card', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Basic Functionality', () => {
    it('should render children', () => {
      render(
        <Card>
          <p>Card content</p>
        </Card>
      )
      
      expect(screen.getByText('Card content')).toBeInTheDocument()
    })

    it('should apply base styling', () => {
      render(<Card>Content</Card>)
      
      const card = screen.getByText('Content').parentElement?.parentElement
      
      // Check base classes
      expect(card).toHaveClass('relative', 'p-4', 'rounded-md', 'backdrop-blur-md')
      expect(card).toHaveClass('bg-gradient-to-b', 'from-white/80', 'to-white/60')
      expect(card).toHaveClass('border')
    })

    it('should render content in relative z-10 wrapper', () => {
      render(<Card>Content</Card>)
      
      const contentWrapper = screen.getByText('Content').parentElement
      expect(contentWrapper).toHaveClass('relative', 'z-10')
    })
  })

  describe('Accent Colors', () => {
    it('should apply no accent color by default', () => {
      render(<Card>Default</Card>)
      
      const card = screen.getByText('Default').parentElement?.parentElement
      expect(card).toHaveClass('border-gray-200')
      expect(card).not.toHaveClass('before:content-[""]')
    })

    it('should apply purple accent color', () => {
      render(<Card accentColor="purple">Purple card</Card>)
      
      const card = screen.getByText('Purple card').parentElement?.parentElement
      expect(card).toHaveClass('border-purple-300')
      expect(card).toHaveClass('before:bg-purple-500')
      expect(card).toHaveClass('before:shadow-[0_0_10px_2px_rgba(168,85,247,0.4)]')
    })

    it('should apply green accent color', () => {
      render(<Card accentColor="green">Green card</Card>)
      
      const card = screen.getByText('Green card').parentElement?.parentElement
      expect(card).toHaveClass('border-emerald-300')
      expect(card).toHaveClass('before:bg-emerald-500')
      expect(card).toHaveClass('after:bg-gradient-to-b', 'from-emerald-100')
    })

    it('should apply pink accent color', () => {
      render(<Card accentColor="pink">Pink card</Card>)
      
      const card = screen.getByText('Pink card').parentElement?.parentElement
      expect(card).toHaveClass('border-pink-300')
      expect(card).toHaveClass('before:bg-pink-500')
    })

    it('should apply blue accent color', () => {
      render(<Card accentColor="blue">Blue card</Card>)
      
      const card = screen.getByText('Blue card').parentElement?.parentElement
      expect(card).toHaveClass('border-blue-300')
      expect(card).toHaveClass('before:bg-blue-500')
    })

    it('should apply orange accent color', () => {
      render(<Card accentColor="orange">Orange card</Card>)
      
      const card = screen.getByText('Orange card').parentElement?.parentElement
      expect(card).toHaveClass('border-orange-300')
      expect(card).toHaveClass('before:bg-orange-500')
    })
  })

  describe('Variants', () => {
    it('should apply default variant', () => {
      render(<Card variant="default">Default variant</Card>)
      
      const card = screen.getByText('Default variant').parentElement?.parentElement
      expect(card).toHaveClass('border')
    })

    it('should apply bordered variant', () => {
      render(<Card variant="bordered">Bordered variant</Card>)
      
      const card = screen.getByText('Bordered variant').parentElement?.parentElement
      expect(card).toHaveClass('border')
    })
  })

  describe('Hover Effects', () => {
    it('should show hover effects', () => {
      render(<Card>Hoverable</Card>)
      
      const card = screen.getByText('Hoverable').parentElement?.parentElement
      
      // Check shadow transitions
      expect(card).toHaveClass('shadow-[0_10px_30px_-15px_rgba(0,0,0,0.1)]')
      expect(card).toHaveClass('hover:shadow-[0_15px_40px_-15px_rgba(0,0,0,0.2)]')
      expect(card).toHaveClass('transition-all', 'duration-300')
    })
  })

  describe('Event Handlers', () => {
    it('should handle click events if onClick provided', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()
      
      render(
        <Card onClick={handleClick}>
          Clickable card
        </Card>
      )
      
      const card = screen.getByText('Clickable card').parentElement?.parentElement
      await user.click(card!)
      
      expect(handleClick).toHaveBeenCalledOnce()
    })

    it('should forward HTML div attributes', () => {
      render(
        <Card 
          id="test-card"
          data-testid="custom-card"
          role="article"
        >
          Card with attributes
        </Card>
      )
      
      const card = screen.getByTestId('custom-card')
      expect(card).toHaveAttribute('id', 'test-card')
      expect(card).toHaveAttribute('role', 'article')
    })
  })

  describe('Custom Styling', () => {
    it('should accept custom className', () => {
      render(
        <Card className="custom-class mt-8">
          Custom styled
        </Card>
      )
      
      const card = screen.getByText('Custom styled').parentElement?.parentElement
      expect(card).toHaveClass('custom-class', 'mt-8')
    })

    it('should merge custom className with default styles', () => {
      render(
        <Card className="shadow-2xl" accentColor="purple">
          Merged styles
        </Card>
      )
      
      const card = screen.getByText('Merged styles').parentElement?.parentElement
      expect(card).toHaveClass('shadow-2xl')
      expect(card).toHaveClass('border-purple-300') // Should still have accent styles
    })
  })

  describe('Accent Effects', () => {
    it('should render top accent line for colored cards', () => {
      render(<Card accentColor="pink">Accent line</Card>)
      
      const card = screen.getByText('Accent line').parentElement?.parentElement
      
      // Check before pseudo-element classes
      expect(card).toHaveClass('before:content-[""]')
      expect(card).toHaveClass('before:absolute')
      expect(card).toHaveClass('before:h-[2px]')
      expect(card).toHaveClass('before:bg-pink-500')
    })

    it('should render gradient overlay for colored cards', () => {
      render(<Card accentColor="green">Gradient overlay</Card>)
      
      const card = screen.getByText('Gradient overlay').parentElement?.parentElement
      
      // Check after pseudo-element classes
      expect(card).toHaveClass('after:content-[""]')
      expect(card).toHaveClass('after:bg-gradient-to-b')
      expect(card).toHaveClass('from-emerald-100')
      expect(card).toHaveClass('after:h-16')
      expect(card).toHaveClass('after:pointer-events-none')
    })

    it('should not render accent effects for none color', () => {
      render(<Card accentColor="none">No effects</Card>)
      
      const card = screen.getByText('No effects').parentElement?.parentElement
      
      expect(card).not.toHaveClass('before:content-[""]')
      expect(card).not.toHaveClass('after:content-[""]')
    })
  })
})