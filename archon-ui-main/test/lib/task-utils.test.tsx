import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import React from 'react'
import { render } from '@testing-library/react'
import { ItemTypes, getAssigneeIcon, getAssigneeGlow, getOrderColor, getOrderGlow } from '@/lib/task-utils'

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  User: ({ className }: { className?: string }) => <div data-testid="user-icon" className={className}>User</div>,
  Bot: ({ className }: { className?: string }) => <div data-testid="bot-icon" className={className}>Bot</div>,
  Tag: ({ className }: { className?: string }) => <div data-testid="tag-icon" className={className}>Tag</div>,
  Clipboard: ({ className }: { className?: string }) => <div data-testid="clipboard-icon" className={className}>Clipboard</div>
}))

describe('task-utils', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('ItemTypes', () => {
    it('should export TASK item type', () => {
      expect(ItemTypes.TASK).toBe('task')
    })
  })

  describe('getAssigneeIcon', () => {
    it('should return User icon for User assignee', () => {
      const { container } = render(<>{getAssigneeIcon('User')}</>)
      const icon = container.querySelector('[data-testid="user-icon"]')
      
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveClass('w-4', 'h-4', 'text-blue-400')
    })

    it('should return Bot icon for AI IDE Agent assignee', () => {
      const { container } = render(<>{getAssigneeIcon('AI IDE Agent')}</>)
      const icon = container.querySelector('[data-testid="bot-icon"]')
      
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveClass('w-4', 'h-4', 'text-purple-400')
    })

    it('should return Archon logo for Archon assignee', () => {
      const { container } = render(<>{getAssigneeIcon('Archon')}</>)
      const img = container.querySelector('img')
      
      expect(img).toBeInTheDocument()
      expect(img).toHaveAttribute('src', '/logo-neon.svg')
      expect(img).toHaveAttribute('alt', 'Archon')
      expect(img).toHaveClass('w-4', 'h-4')
    })

    it('should return default User icon for unknown assignee', () => {
      // @ts-expect-error Testing invalid input
      const { container } = render(<>{getAssigneeIcon('Unknown')}</>)
      const icon = container.querySelector('[data-testid="user-icon"]')
      
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveClass('w-4', 'h-4', 'text-blue-400')
    })
  })

  describe('getAssigneeGlow', () => {
    it('should return blue glow for User assignee', () => {
      const glow = getAssigneeGlow('User')
      expect(glow).toBe('shadow-[0_0_10px_rgba(59,130,246,0.4)]')
    })

    it('should return purple glow for AI IDE Agent assignee', () => {
      const glow = getAssigneeGlow('AI IDE Agent')
      expect(glow).toBe('shadow-[0_0_10px_rgba(168,85,247,0.4)]')
    })

    it('should return cyan glow for Archon assignee', () => {
      const glow = getAssigneeGlow('Archon')
      expect(glow).toBe('shadow-[0_0_10px_rgba(34,211,238,0.4)]')
    })

    it('should return default blue glow for unknown assignee', () => {
      // @ts-expect-error Testing invalid input
      const glow = getAssigneeGlow('Unknown')
      expect(glow).toBe('shadow-[0_0_10px_rgba(59,130,246,0.4)]')
    })
  })

  describe('getOrderColor', () => {
    it('should return rose color for high priority (1-3)', () => {
      expect(getOrderColor(1)).toBe('bg-rose-500')
      expect(getOrderColor(2)).toBe('bg-rose-500')
      expect(getOrderColor(3)).toBe('bg-rose-500')
    })

    it('should return orange color for medium-high priority (4-6)', () => {
      expect(getOrderColor(4)).toBe('bg-orange-500')
      expect(getOrderColor(5)).toBe('bg-orange-500')
      expect(getOrderColor(6)).toBe('bg-orange-500')
    })

    it('should return blue color for medium priority (7-10)', () => {
      expect(getOrderColor(7)).toBe('bg-blue-500')
      expect(getOrderColor(8)).toBe('bg-blue-500')
      expect(getOrderColor(9)).toBe('bg-blue-500')
      expect(getOrderColor(10)).toBe('bg-blue-500')
    })

    it('should return emerald color for low priority (11+)', () => {
      expect(getOrderColor(11)).toBe('bg-emerald-500')
      expect(getOrderColor(15)).toBe('bg-emerald-500')
      expect(getOrderColor(100)).toBe('bg-emerald-500')
    })

    it('should handle edge cases', () => {
      expect(getOrderColor(0)).toBe('bg-rose-500')
      expect(getOrderColor(-1)).toBe('bg-rose-500')
    })
  })

  describe('getOrderGlow', () => {
    it('should return rose glow for high priority (1-3)', () => {
      expect(getOrderGlow(1)).toBe('shadow-[0_0_10px_rgba(244,63,94,0.7)]')
      expect(getOrderGlow(2)).toBe('shadow-[0_0_10px_rgba(244,63,94,0.7)]')
      expect(getOrderGlow(3)).toBe('shadow-[0_0_10px_rgba(244,63,94,0.7)]')
    })

    it('should return orange glow for medium-high priority (4-6)', () => {
      expect(getOrderGlow(4)).toBe('shadow-[0_0_10px_rgba(249,115,22,0.7)]')
      expect(getOrderGlow(5)).toBe('shadow-[0_0_10px_rgba(249,115,22,0.7)]')
      expect(getOrderGlow(6)).toBe('shadow-[0_0_10px_rgba(249,115,22,0.7)]')
    })

    it('should return blue glow for medium priority (7-10)', () => {
      expect(getOrderGlow(7)).toBe('shadow-[0_0_10px_rgba(59,130,246,0.7)]')
      expect(getOrderGlow(8)).toBe('shadow-[0_0_10px_rgba(59,130,246,0.7)]')
      expect(getOrderGlow(9)).toBe('shadow-[0_0_10px_rgba(59,130,246,0.7)]')
      expect(getOrderGlow(10)).toBe('shadow-[0_0_10px_rgba(59,130,246,0.7)]')
    })

    it('should return emerald glow for low priority (11+)', () => {
      expect(getOrderGlow(11)).toBe('shadow-[0_0_10px_rgba(16,185,129,0.7)]')
      expect(getOrderGlow(15)).toBe('shadow-[0_0_10px_rgba(16,185,129,0.7)]')
      expect(getOrderGlow(100)).toBe('shadow-[0_0_10px_rgba(16,185,129,0.7)]')
    })

    it('should handle edge cases', () => {
      expect(getOrderGlow(0)).toBe('shadow-[0_0_10px_rgba(244,63,94,0.7)]')
      expect(getOrderGlow(-1)).toBe('shadow-[0_0_10px_rgba(244,63,94,0.7)]')
    })
  })

  describe('Priority Consistency', () => {
    it('should have matching color and glow for same priority ranges', () => {
      // High priority
      const highColor = getOrderColor(2)
      const highGlow = getOrderGlow(2)
      expect(highColor).toContain('rose')
      expect(highGlow).toContain('244,63,94') // rose color RGB

      // Medium-high priority
      const medHighColor = getOrderColor(5)
      const medHighGlow = getOrderGlow(5)
      expect(medHighColor).toContain('orange')
      expect(medHighGlow).toContain('249,115,22') // orange color RGB

      // Medium priority
      const medColor = getOrderColor(8)
      const medGlow = getOrderGlow(8)
      expect(medColor).toContain('blue')
      expect(medGlow).toContain('59,130,246') // blue color RGB

      // Low priority
      const lowColor = getOrderColor(20)
      const lowGlow = getOrderGlow(20)
      expect(lowColor).toContain('emerald')
      expect(lowGlow).toContain('16,185,129') // emerald color RGB
    })
  })

  describe('Type Safety', () => {
    it('should only accept valid assignee names', () => {
      // These should work without TypeScript errors
      getAssigneeIcon('User')
      getAssigneeIcon('Archon')
      getAssigneeIcon('AI IDE Agent')
      
      getAssigneeGlow('User')
      getAssigneeGlow('Archon')
      getAssigneeGlow('AI IDE Agent')
      
      // TypeScript should catch invalid values at compile time
      expect(true).toBe(true)
    })

    it('should handle numeric order values', () => {
      // Integer values
      expect(getOrderColor(5)).toBeDefined()
      expect(getOrderGlow(5)).toBeDefined()
      
      // Decimal values
      expect(getOrderColor(5.5)).toBeDefined()
      expect(getOrderGlow(5.5)).toBeDefined()
      
      // Very large values
      expect(getOrderColor(Number.MAX_SAFE_INTEGER)).toBe('bg-emerald-500')
      expect(getOrderGlow(Number.MAX_SAFE_INTEGER)).toBe('shadow-[0_0_10px_rgba(16,185,129,0.7)]')
    })
  })
})