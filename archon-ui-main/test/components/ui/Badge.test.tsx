import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from '@/components/ui/Badge'

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

describe('Badge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Basic Functionality', () => {
    it('should display text', () => {
      render(<Badge>Test Badge</Badge>)
      
      expect(screen.getByText('Test Badge')).toBeInTheDocument()
    })

    it('should render as inline span element', () => {
      render(<Badge>Inline Badge</Badge>)
      
      const badge = screen.getByText('Inline Badge')
      expect(badge.tagName).toBe('SPAN')
      expect(badge).toHaveClass('inline-flex')
    })

    it('should apply base styling', () => {
      render(<Badge>Styled Badge</Badge>)
      
      const badge = screen.getByText('Styled Badge')
      expect(badge).toHaveClass('items-center', 'text-xs', 'px-2', 'py-1', 'rounded')
    })
  })

  describe('Color Variants', () => {
    describe('Solid Variant', () => {
      it('should apply gray solid color by default', () => {
        render(<Badge variant="solid">Default Gray</Badge>)
        
        const badge = screen.getByText('Default Gray')
        expect(badge).toHaveClass('bg-gray-200', 'text-gray-700')
      })

      it('should apply purple solid color', () => {
        render(<Badge variant="solid" color="purple">Purple Badge</Badge>)
        
        const badge = screen.getByText('Purple Badge')
        expect(badge).toHaveClass('bg-purple-500/10', 'text-purple-500')
      })

      it('should apply green solid color', () => {
        render(<Badge variant="solid" color="green">Green Badge</Badge>)
        
        const badge = screen.getByText('Green Badge')
        expect(badge).toHaveClass('bg-emerald-500/10', 'text-emerald-500')
      })

      it('should apply pink solid color', () => {
        render(<Badge variant="solid" color="pink">Pink Badge</Badge>)
        
        const badge = screen.getByText('Pink Badge')
        expect(badge).toHaveClass('bg-pink-500/10', 'text-pink-500')
      })

      it('should apply blue solid color', () => {
        render(<Badge variant="solid" color="blue">Blue Badge</Badge>)
        
        const badge = screen.getByText('Blue Badge')
        expect(badge).toHaveClass('bg-blue-500/10', 'text-blue-500')
      })
    })

    describe('Outline Variant', () => {
      it('should apply gray outline color by default', () => {
        render(<Badge>Default Outline</Badge>)
        
        const badge = screen.getByText('Default Outline')
        expect(badge).toHaveClass('border', 'border-gray-300', 'text-gray-700')
      })

      it('should apply purple outline color', () => {
        render(<Badge color="purple">Purple Outline</Badge>)
        
        const badge = screen.getByText('Purple Outline')
        expect(badge).toHaveClass('border', 'border-purple-300', 'text-purple-600')
      })

      it('should apply green outline color', () => {
        render(<Badge color="green">Green Outline</Badge>)
        
        const badge = screen.getByText('Green Outline')
        expect(badge).toHaveClass('border', 'border-emerald-300', 'text-emerald-600')
      })

      it('should apply pink outline color', () => {
        render(<Badge color="pink">Pink Outline</Badge>)
        
        const badge = screen.getByText('Pink Outline')
        expect(badge).toHaveClass('border', 'border-pink-300', 'text-pink-600')
      })

      it('should apply blue outline color', () => {
        render(<Badge color="blue">Blue Outline</Badge>)
        
        const badge = screen.getByText('Blue Outline')
        expect(badge).toHaveClass('border', 'border-blue-300', 'text-blue-600')
      })
    })
  })

  describe('Complex Content', () => {
    it('should support React node children', () => {
      render(
        <Badge>
          <span data-testid="icon">🔥</span>
          <span>With Icon</span>
        </Badge>
      )
      
      expect(screen.getByTestId('icon')).toBeInTheDocument()
      expect(screen.getByText('With Icon')).toBeInTheDocument()
    })

    it('should support nested elements', () => {
      render(
        <Badge>
          <div>
            <strong>Bold</strong> and <em>italic</em>
          </div>
        </Badge>
      )
      
      expect(screen.getByText('Bold')).toBeInTheDocument()
      expect(screen.getByText('and')).toBeInTheDocument()
      expect(screen.getByText('italic')).toBeInTheDocument()
    })
  })

  describe('Custom Styling', () => {
    it('should accept custom className', () => {
      render(<Badge className="custom-badge mt-4">Custom</Badge>)
      
      const badge = screen.getByText('Custom')
      expect(badge).toHaveClass('custom-badge', 'mt-4')
    })

    it('should merge custom className with default styles', () => {
      render(<Badge className="font-bold" color="purple">Bold Badge</Badge>)
      
      const badge = screen.getByText('Bold Badge')
      expect(badge).toHaveClass('font-bold')
      expect(badge).toHaveClass('text-purple-600') // Should still have color styles
    })
  })

  describe('HTML Attributes', () => {
    it('should forward HTML span attributes', () => {
      render(
        <Badge 
          id="test-badge"
          data-testid="custom-badge"
          title="Badge tooltip"
        >
          With Attributes
        </Badge>
      )
      
      const badge = screen.getByTestId('custom-badge')
      expect(badge).toHaveAttribute('id', 'test-badge')
      expect(badge).toHaveAttribute('title', 'Badge tooltip')
    })

    it('should handle click events', () => {
      const handleClick = vi.fn()
      
      render(
        <Badge onClick={handleClick}>
          Clickable Badge
        </Badge>
      )
      
      const badge = screen.getByText('Clickable Badge')
      badge.click()
      
      expect(handleClick).toHaveBeenCalledOnce()
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty children gracefully', () => {
      render(<Badge>{''}</Badge>)
      
      // Badge should still render even with empty content
      const badges = document.querySelectorAll('.inline-flex')
      expect(badges.length).toBeGreaterThan(0)
    })

    it('should handle long text content', () => {
      const longText = 'This is a very long badge text that should still display properly'
      render(<Badge>{longText}</Badge>)
      
      expect(screen.getByText(longText)).toBeInTheDocument()
    })

    it('should handle numeric content', () => {
      render(<Badge>{42}</Badge>)
      
      expect(screen.getByText('42')).toBeInTheDocument()
    })
  })
})