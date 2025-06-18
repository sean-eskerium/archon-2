import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import { Card } from '@/components/ui/Card'

describe('Card', () => {
  describe('Content Rendering', () => {
    it('should render children content', () => {
      render(
        <Card>
          <h1>Test Title</h1>
          <p>Test content</p>
        </Card>
      )
      
      expect(screen.getByText('Test Title')).toBeInTheDocument()
      expect(screen.getByText('Test content')).toBeInTheDocument()
    })

    it('should wrap content in a z-10 container for proper layering', () => {
      render(
        <Card>
          <div data-testid="content">Content</div>
        </Card>
      )
      
      const content = screen.getByTestId('content')
      const wrapper = content.parentElement
      
      // Verify content is wrapped for proper z-index layering
      expect(wrapper?.className).toContain('z-10')
    })

    it('should pass through HTML attributes', () => {
      const onClick = vi.fn()
      render(
        <Card data-testid="card" onClick={onClick} aria-label="Test card">
          Content
        </Card>
      )
      
      const card = screen.getByTestId('card')
      expect(card).toHaveAttribute('aria-label', 'Test card')
      
      card.click()
      expect(onClick).toHaveBeenCalled()
    })
  })

  describe('Visual Hierarchy', () => {
    it('should apply gradient background for depth perception', () => {
      const { container } = render(<Card>Content</Card>)
      const card = container.firstChild as HTMLElement
      
      // Check for gradient background classes
      expect(card.className).toMatch(/bg-gradient-to-b/)
      expect(card.className).toMatch(/from-.*to-/)
    })

    it('should have proper spacing and rounded corners', () => {
      const { container } = render(<Card>Content</Card>)
      const card = container.firstChild as HTMLElement
      
      // Verify basic layout properties
      expect(card.className).toMatch(/p-\d+/) // padding
      expect(card.className).toMatch(/rounded/) // rounded corners
    })
  })

  describe('Accent Color Functionality', () => {
    it('should render without accent styling by default', () => {
      const { container } = render(<Card>Content</Card>)
      const card = container.firstChild as HTMLElement
      
      // Default should not have before/after pseudo elements
      expect(card.className).not.toContain('before:content')
      expect(card.className).not.toContain('after:content')
    })

    it.each([
      'purple', 'green', 'pink', 'blue', 'orange'
    ] as const)('should apply %s accent color styling', (color) => {
      const { container } = render(
        <Card accentColor={color}>Content</Card>
      )
      const card = container.firstChild as HTMLElement
      
      // Should have pseudo elements for accent
      expect(card.className).toContain('before:content')
      expect(card.className).toContain('after:content')
      
      // Should have color-specific classes
      expect(card.className).toMatch(new RegExp(`border-${color}`))
    })

    it('should create visual hierarchy with accent colors', () => {
      const { container } = render(
        <Card accentColor="purple">Important content</Card>
      )
      const card = container.firstChild as HTMLElement
      
      // Check for top accent line
      expect(card.className).toContain('before:absolute')
      expect(card.className).toContain('before:top-[0px]')
      expect(card.className).toContain('before:h-[2px]')
      
      // Check for gradient overlay
      expect(card.className).toContain('after:absolute')
      expect(card.className).toContain('after:bg-gradient-to-b')
    })
  })

  describe('Interaction States', () => {
    it('should have hover effects for better interactivity', () => {
      const { container } = render(<Card>Content</Card>)
      const card = container.firstChild as HTMLElement
      
      // Should have hover shadow classes
      expect(card.className).toContain('hover:shadow')
      expect(card.className).toContain('transition')
    })

    it('should handle dark mode styling', () => {
      const { container } = render(<Card>Content</Card>)
      const card = container.firstChild as HTMLElement
      
      // Should have dark mode variants
      expect(card.className).toMatch(/dark:/)
    })
  })

  describe('Composability', () => {
    it('should merge custom className with default styles', () => {
      const { container } = render(
        <Card className="custom-class mt-8">Content</Card>
      )
      const card = container.firstChild as HTMLElement
      
      // Should include custom class
      expect(card.className).toContain('custom-class')
      expect(card.className).toContain('mt-8')
      
      // Should still have default card styling
      expect(card.className).toContain('relative')
      expect(card.className).toContain('rounded')
    })

    it('should work as a container for complex layouts', () => {
      render(
        <Card>
          <header data-testid="header">Header</header>
          <main data-testid="main">Main content</main>
          <footer data-testid="footer">Footer</footer>
        </Card>
      )
      
      expect(screen.getByTestId('header')).toBeInTheDocument()
      expect(screen.getByTestId('main')).toBeInTheDocument()
      expect(screen.getByTestId('footer')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should render as a div by default', () => {
      const { container } = render(<Card>Content</Card>)
      expect(container.firstChild?.nodeName).toBe('DIV')
    })

    it('should support ARIA attributes', () => {
      render(
        <Card role="article" aria-labelledby="title">
          <h2 id="title">Article Title</h2>
          <p>Article content</p>
        </Card>
      )
      
      const card = screen.getByRole('article')
      expect(card).toHaveAttribute('aria-labelledby', 'title')
    })
  })

  describe('Performance', () => {
    it('should not re-render unnecessarily', () => {
      const { rerender } = render(
        <Card accentColor="purple">Content</Card>
      )
      
      const initialCard = screen.getByText('Content').parentElement?.parentElement
      const initialClassName = initialCard?.className
      
      // Re-render with same props
      rerender(<Card accentColor="purple">Content</Card>)
      
      const updatedCard = screen.getByText('Content').parentElement?.parentElement
      expect(updatedCard?.className).toBe(initialClassName)
    })
  })
})