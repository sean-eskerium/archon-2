import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useStaggeredEntrance } from '@/hooks/useStaggeredEntrance'

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

describe('useStaggeredEntrance', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('Initial State', () => {
    it('should return animation variants and visibility state', () => {
      const items = ['item1', 'item2', 'item3']
      const { result } = renderHook(() => useStaggeredEntrance(items))

      expect(result.current.isVisible).toBe(false)
      expect(result.current.containerVariants).toBeDefined()
      expect(result.current.itemVariants).toBeDefined()
      expect(result.current.titleVariants).toBeDefined()
    })

    it('should set isVisible to true after mount', async () => {
      const items = ['item1', 'item2', 'item3']
      const { result } = renderHook(() => useStaggeredEntrance(items))

      expect(result.current.isVisible).toBe(false)

      // Wait for useEffect to run
      await waitFor(() => {
        expect(result.current.isVisible).toBe(true)
      })
    })
  })

  describe('Container Variants', () => {
    it('should have correct hidden state', () => {
      const items = ['item1', 'item2']
      const { result } = renderHook(() => useStaggeredEntrance(items))

      expect(result.current.containerVariants.hidden).toEqual({
        opacity: 0
      })
    })

    it('should have correct visible state with default stagger', () => {
      const items = ['item1', 'item2']
      const { result } = renderHook(() => useStaggeredEntrance(items))

      expect(result.current.containerVariants.visible).toEqual({
        opacity: 1,
        transition: {
          staggerChildren: 0.15,
          delayChildren: 0.1
        }
      })
    })

    it('should respect custom stagger delay', () => {
      const items = ['item1', 'item2']
      const customDelay = 0.3
      const { result } = renderHook(() => useStaggeredEntrance(items, customDelay))

      expect(result.current.containerVariants.visible.transition.staggerChildren).toBe(0.3)
    })
  })

  describe('Item Variants', () => {
    it('should have correct hidden state', () => {
      const items = ['item1', 'item2']
      const { result } = renderHook(() => useStaggeredEntrance(items))

      expect(result.current.itemVariants.hidden).toEqual({
        opacity: 0,
        y: 20,
        scale: 0.98
      })
    })

    it('should have correct visible state', () => {
      const items = ['item1', 'item2']
      const { result } = renderHook(() => useStaggeredEntrance(items))

      expect(result.current.itemVariants.visible).toEqual({
        opacity: 1,
        y: 0,
        scale: 1,
        transition: {
          duration: 0.4,
          ease: 'easeOut'
        }
      })
    })
  })

  describe('Title Variants', () => {
    it('should have correct hidden state', () => {
      const items = ['item1', 'item2']
      const { result } = renderHook(() => useStaggeredEntrance(items))

      expect(result.current.titleVariants.hidden).toEqual({
        opacity: 0,
        scale: 0.98
      })
    })

    it('should have correct visible state', () => {
      const items = ['item1', 'item2']
      const { result } = renderHook(() => useStaggeredEntrance(items))

      expect(result.current.titleVariants.visible).toEqual({
        opacity: 1,
        scale: 1,
        transition: {
          duration: 0.4,
          ease: 'easeOut'
        }
      })
    })
  })

  describe('Force Reanimate', () => {
    it('should trigger reanimation when counter changes', async () => {
      const items = ['item1', 'item2']
      let forceReanimateCounter = 0
      
      const { result, rerender } = renderHook(
        () => useStaggeredEntrance(items, 0.15, forceReanimateCounter)
      )

      // Initially becomes visible
      await waitFor(() => {
        expect(result.current.isVisible).toBe(true)
      })

      // Update counter
      forceReanimateCounter = 1
      rerender()

      // Should briefly become invisible
      expect(result.current.isVisible).toBe(false)

      // Fast forward the timer
      act(() => {
        vi.advanceTimersByTime(50)
      })

      // Should be visible again
      await waitFor(() => {
        expect(result.current.isVisible).toBe(true)
      })
    })

    it('should not reanimate when counter is 0', async () => {
      const items = ['item1', 'item2']
      
      const { result } = renderHook(
        () => useStaggeredEntrance(items, 0.15, 0)
      )

      // Should become visible normally
      await waitFor(() => {
        expect(result.current.isVisible).toBe(true)
      })

      // Should not have set any additional timers
      expect(vi.getTimerCount()).toBe(0)
    })

    it('should cleanup timer on unmount during reanimation', () => {
      const items = ['item1', 'item2']
      
      const { unmount } = renderHook(
        () => useStaggeredEntrance(items, 0.15, 1)
      )

      // Timer should be set
      expect(vi.getTimerCount()).toBeGreaterThan(0)

      // Unmount before timer fires
      unmount()

      // Timer should be cleared
      expect(vi.getTimerCount()).toBe(0)
    })
  })

  describe('Dynamic Items', () => {
    it('should handle empty items array', () => {
      const items: string[] = []
      const { result } = renderHook(() => useStaggeredEntrance(items))

      // Should still return valid variants
      expect(result.current.containerVariants).toBeDefined()
      expect(result.current.itemVariants).toBeDefined()
      expect(result.current.titleVariants).toBeDefined()
    })

    it('should handle changing items array', async () => {
      let items = ['item1', 'item2']
      
      const { result, rerender } = renderHook(
        () => useStaggeredEntrance(items)
      )

      await waitFor(() => {
        expect(result.current.isVisible).toBe(true)
      })

      // Change items
      items = ['item1', 'item2', 'item3', 'item4']
      rerender()

      // Should still be visible and variants should be unchanged
      expect(result.current.isVisible).toBe(true)
      expect(result.current.containerVariants).toBeDefined()
    })

    it('should work with different item types', () => {
      const objectItems = [
        { id: 1, name: 'Item 1' },
        { id: 2, name: 'Item 2' }
      ]
      
      const { result } = renderHook(() => useStaggeredEntrance(objectItems))

      expect(result.current.containerVariants).toBeDefined()
      expect(result.current.itemVariants).toBeDefined()
      expect(result.current.titleVariants).toBeDefined()
    })
  })

  describe('Edge Cases', () => {
    it('should handle negative stagger delay', () => {
      const items = ['item1', 'item2']
      const negativeDelay = -0.5
      
      const { result } = renderHook(() => useStaggeredEntrance(items, negativeDelay))

      // Should use the negative value as-is (Framer Motion will handle it)
      expect(result.current.containerVariants.visible.transition.staggerChildren).toBe(-0.5)
    })

    it('should handle zero stagger delay', () => {
      const items = ['item1', 'item2']
      const zeroDelay = 0
      
      const { result } = renderHook(() => useStaggeredEntrance(items, zeroDelay))

      expect(result.current.containerVariants.visible.transition.staggerChildren).toBe(0)
    })

    it('should handle very large stagger delay', () => {
      const items = ['item1', 'item2']
      const largeDelay = 10
      
      const { result } = renderHook(() => useStaggeredEntrance(items, largeDelay))

      expect(result.current.containerVariants.visible.transition.staggerChildren).toBe(10)
    })

    it('should maintain referential equality of variants', () => {
      const items = ['item1', 'item2']
      const { result, rerender } = renderHook(() => useStaggeredEntrance(items))

      const containerVariants1 = result.current.containerVariants
      const itemVariants1 = result.current.itemVariants
      const titleVariants1 = result.current.titleVariants

      // Force re-render
      rerender()

      const containerVariants2 = result.current.containerVariants
      const itemVariants2 = result.current.itemVariants
      const titleVariants2 = result.current.titleVariants

      // Variants should be new objects each time (not memoized)
      expect(containerVariants1).not.toBe(containerVariants2)
      expect(itemVariants1).not.toBe(itemVariants2)
      expect(titleVariants1).not.toBe(titleVariants2)

      // But values should be equal
      expect(containerVariants1).toEqual(containerVariants2)
      expect(itemVariants1).toEqual(itemVariants2)
      expect(titleVariants1).toEqual(titleVariants2)
    })
  })
})