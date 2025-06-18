import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useNeonGlow } from '@/hooks/useNeonGlow'

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

describe('useNeonGlow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock DOM methods
    document.head.appendChild = vi.fn()
    document.head.removeChild = vi.fn()
    document.head.contains = vi.fn(() => true)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Initial State', () => {
    it('should return initial state correctly', () => {
      const { result } = renderHook(() => useNeonGlow())

      expect(result.current.containerRef.current).toBeNull()
      expect(result.current.isAnimating).toBe(false)
      expect(typeof result.current.start).toBe('function')
      expect(typeof result.current.stop).toBe('function')
      expect(typeof result.current.updateOptions).toBe('function')
    })

    it('should accept initial options', () => {
      const initialOptions = {
        opacity: 0.5,
        blur: 3,
        size: 200,
        color: 'purple',
        speed: 3000,
        enabled: false
      }

      const { result } = renderHook(() => useNeonGlow(initialOptions))

      // Should start not animating since enabled is false
      expect(result.current.isAnimating).toBe(false)
    })
  })

  describe('Animation Control', () => {
    it('should start animation when start is called', () => {
      const mockDiv = document.createElement('div')
      Object.defineProperty(mockDiv, 'clientWidth', { value: 500, configurable: true })
      Object.defineProperty(mockDiv, 'clientHeight', { value: 500, configurable: true })
      mockDiv.appendChild = vi.fn()
      mockDiv.removeChild = vi.fn()
      mockDiv.contains = vi.fn(() => true)
      mockDiv.style.setProperty = vi.fn()

      const { result } = renderHook(() => useNeonGlow())
      
      // Set the ref
      Object.defineProperty(result.current.containerRef, 'current', {
        value: mockDiv,
        writable: true
      })

      act(() => {
        result.current.start()
      })

      expect(result.current.isAnimating).toBe(true)
      expect(mockDiv.appendChild).toHaveBeenCalled()
    })

    it('should not start if already animating', () => {
      const mockDiv = document.createElement('div')
      mockDiv.appendChild = vi.fn()

      const { result } = renderHook(() => useNeonGlow())
      
      Object.defineProperty(result.current.containerRef, 'current', {
        value: mockDiv,
        writable: true
      })

      act(() => {
        result.current.start()
      })

      const appendCallCount = mockDiv.appendChild.mock.calls.length

      act(() => {
        result.current.start() // Try to start again
      })

      // Should not create more elements
      expect(mockDiv.appendChild).toHaveBeenCalledTimes(appendCallCount)
    })

    it('should not start if enabled is false', () => {
      const mockDiv = document.createElement('div')
      mockDiv.appendChild = vi.fn()

      const { result } = renderHook(() => useNeonGlow({ enabled: false }))
      
      Object.defineProperty(result.current.containerRef, 'current', {
        value: mockDiv,
        writable: true
      })

      act(() => {
        result.current.start()
      })

      expect(result.current.isAnimating).toBe(false)
      expect(mockDiv.appendChild).not.toHaveBeenCalled()
    })

    it('should stop animation and cleanup', () => {
      const mockDiv = document.createElement('div')
      const mockElement = document.createElement('div')
      mockDiv.appendChild = vi.fn()
      mockDiv.removeChild = vi.fn()
      mockDiv.contains = vi.fn(() => true)

      const { result } = renderHook(() => useNeonGlow())
      
      Object.defineProperty(result.current.containerRef, 'current', {
        value: mockDiv,
        writable: true
      })

      act(() => {
        result.current.start()
      })

      // Manually add element to simulate created particles
      result.current.containerRef.current.appendChild(mockElement)

      act(() => {
        result.current.stop()
      })

      expect(result.current.isAnimating).toBe(false)
    })
  })

  describe('Options Update', () => {
    it('should update options dynamically', () => {
      const mockDiv = document.createElement('div')
      mockDiv.style.setProperty = vi.fn()

      const { result } = renderHook(() => useNeonGlow())
      
      Object.defineProperty(result.current.containerRef, 'current', {
        value: mockDiv,
        writable: true
      })

      act(() => {
        result.current.start()
      })

      act(() => {
        result.current.updateOptions({
          opacity: 0.3,
          blur: 5,
          speed: 1000
        })
      })

      // Should update CSS properties
      expect(mockDiv.style.setProperty).toHaveBeenCalledWith('--neon-opacity', '0.3')
      expect(mockDiv.style.setProperty).toHaveBeenCalledWith('--neon-blur', '5px')
      expect(mockDiv.style.setProperty).toHaveBeenCalledWith('--neon-speed', '1000ms')
    })

    it('should recreate pattern when size changes', () => {
      const mockDiv = document.createElement('div')
      Object.defineProperty(mockDiv, 'clientWidth', { value: 500, configurable: true })
      Object.defineProperty(mockDiv, 'clientHeight', { value: 500, configurable: true })
      mockDiv.appendChild = vi.fn()
      mockDiv.removeChild = vi.fn()
      mockDiv.contains = vi.fn(() => false)
      mockDiv.style.setProperty = vi.fn()

      const { result } = renderHook(() => useNeonGlow())
      
      Object.defineProperty(result.current.containerRef, 'current', {
        value: mockDiv,
        writable: true
      })

      act(() => {
        result.current.start()
      })

      const initialAppendCount = (mockDiv.appendChild as any).mock.calls.length

      act(() => {
        result.current.updateOptions({ size: 150 })
      })

      // Should recreate elements
      expect((mockDiv.appendChild as any).mock.calls.length).toBeGreaterThan(initialAppendCount)
    })
  })

  describe('Heart Chakra Pattern', () => {
    it('should create heart-shaped pattern with correct number of elements', () => {
      const mockDiv = document.createElement('div')
      Object.defineProperty(mockDiv, 'clientWidth', { value: 500, configurable: true })
      Object.defineProperty(mockDiv, 'clientHeight', { value: 500, configurable: true })
      mockDiv.appendChild = vi.fn()
      mockDiv.style.setProperty = vi.fn()

      const { result } = renderHook(() => useNeonGlow())
      
      Object.defineProperty(result.current.containerRef, 'current', {
        value: mockDiv,
        writable: true
      })

      act(() => {
        result.current.start()
      })

      // Should create 20 heart points + 12 ray points = 32 elements
      expect(mockDiv.appendChild).toHaveBeenCalledTimes(32)
    })

    it('should apply correct styles to particles', () => {
      const mockDiv = document.createElement('div')
      Object.defineProperty(mockDiv, 'clientWidth', { value: 500, configurable: true })
      Object.defineProperty(mockDiv, 'clientHeight', { value: 500, configurable: true })
      const appendedElements: HTMLElement[] = []
      
      mockDiv.appendChild = vi.fn((element: HTMLElement) => {
        appendedElements.push(element)
      })
      mockDiv.style.setProperty = vi.fn()

      const { result } = renderHook(() => useNeonGlow())
      
      Object.defineProperty(result.current.containerRef, 'current', {
        value: mockDiv,
        writable: true
      })

      act(() => {
        result.current.start()
      })

      // Check first particle
      const firstParticle = appendedElements[0]
      expect(firstParticle.className).toBe('neon-glow-particle')
      expect(firstParticle.style.position).toBe('absolute')
      expect(firstParticle.style.borderRadius).toBe('50%')
      expect(firstParticle.style.pointerEvents).toBe('none')
      expect(firstParticle.style.animation).toContain('neonPulse')
    })
  })

  describe('CSS Setup', () => {
    it('should add CSS keyframes on mount', () => {
      renderHook(() => useNeonGlow())

      expect(document.head.appendChild).toHaveBeenCalled()
      const styleCall = (document.head.appendChild as any).mock.calls[0][0]
      expect(styleCall.textContent).toContain('@keyframes neonPulse')
      expect(styleCall.textContent).toContain('.neon-glow-container')
    })

    it('should cleanup CSS on unmount', () => {
      const { unmount } = renderHook(() => useNeonGlow())

      unmount()

      expect(document.head.removeChild).toHaveBeenCalled()
    })
  })

  describe('Edge Cases', () => {
    it('should handle missing container ref gracefully', () => {
      const { result } = renderHook(() => useNeonGlow())

      // Start without setting ref
      expect(() => {
        act(() => {
          result.current.start()
        })
      }).not.toThrow()

      expect(result.current.isAnimating).toBe(false)
    })

    it('should cleanup on unmount even if animating', () => {
      const mockDiv = document.createElement('div')
      mockDiv.appendChild = vi.fn()
      mockDiv.removeChild = vi.fn()
      mockDiv.contains = vi.fn(() => true)

      const { result, unmount } = renderHook(() => useNeonGlow())
      
      Object.defineProperty(result.current.containerRef, 'current', {
        value: mockDiv,
        writable: true
      })

      act(() => {
        result.current.start()
      })

      expect(result.current.isAnimating).toBe(true)

      unmount()

      // Should have called cleanup
      expect(mockDiv.removeChild).toHaveBeenCalled()
    })

    it('should handle rapid start/stop calls', () => {
      const mockDiv = document.createElement('div')
      mockDiv.appendChild = vi.fn()
      mockDiv.removeChild = vi.fn()
      mockDiv.contains = vi.fn(() => true)
      mockDiv.style.setProperty = vi.fn()

      const { result } = renderHook(() => useNeonGlow())
      
      Object.defineProperty(result.current.containerRef, 'current', {
        value: mockDiv,
        writable: true
      })

      // Rapid fire
      act(() => {
        result.current.start()
        result.current.stop()
        result.current.start()
        result.current.stop()
        result.current.start()
      })

      expect(result.current.isAnimating).toBe(true)
    })
  })
})