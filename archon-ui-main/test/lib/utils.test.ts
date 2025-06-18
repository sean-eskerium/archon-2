import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { cn } from '@/lib/utils'

describe('utils', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('cn - Class Name Utility', () => {
    it('should merge single class name', () => {
      const result = cn('text-red-500')
      expect(result).toBe('text-red-500')
    })

    it('should merge multiple class names', () => {
      const result = cn('text-red-500', 'bg-blue-500', 'p-4')
      expect(result).toBe('text-red-500 bg-blue-500 p-4')
    })

    it('should handle conditional classes', () => {
      const isActive = true
      const isDisabled = false
      
      const result = cn(
        'base-class',
        isActive && 'active-class',
        isDisabled && 'disabled-class'
      )
      
      expect(result).toBe('base-class active-class')
    })

    it('should handle object syntax', () => {
      const result = cn({
        'text-red-500': true,
        'bg-blue-500': false,
        'font-bold': true
      })
      
      expect(result).toBe('text-red-500 font-bold')
    })

    it('should handle array syntax', () => {
      const result = cn(['text-red-500', 'bg-blue-500'], 'p-4')
      expect(result).toBe('text-red-500 bg-blue-500 p-4')
    })

    it('should merge conflicting Tailwind classes correctly', () => {
      // twMerge should handle conflicts intelligently
      const result = cn('text-red-500', 'text-blue-500')
      expect(result).toBe('text-blue-500') // Later class wins
      
      const result2 = cn('p-4', 'p-8')
      expect(result2).toBe('p-8') // Later padding wins
      
      const result3 = cn('mt-4 mb-4', 'my-8')
      expect(result3).toBe('my-8') // Shorthand wins
    })

    it('should handle undefined and null values', () => {
      const result = cn('text-red-500', undefined, null, 'bg-blue-500')
      expect(result).toBe('text-red-500 bg-blue-500')
    })

    it('should handle empty strings', () => {
      const result = cn('text-red-500', '', 'bg-blue-500')
      expect(result).toBe('text-red-500 bg-blue-500')
    })

    it('should handle no arguments', () => {
      const result = cn()
      expect(result).toBe('')
    })

    it('should handle complex nested conditions', () => {
      const theme = 'dark'
      const size: 'small' | 'medium' | 'large' = 'large'
      const isHovered = true
      
      const result = cn(
        'base-button',
        theme === 'dark' && 'dark:bg-gray-800',
        {
          'text-sm': size === 'small',
          'text-base': size === 'medium',
          'text-lg': size === 'large',
        },
        isHovered && ['hover:bg-opacity-80', 'transition-colors']
      )
      
      expect(result).toBe('base-button dark:bg-gray-800 text-lg hover:bg-opacity-80 transition-colors')
    })

    it('should handle mixed input types', () => {
      const result = cn(
        'string-class',
        ['array', 'classes'],
        {
          'object-true': true,
          'object-false': false
        },
        undefined,
        null,
        true && 'conditional-true',
        false && 'conditional-false'
      )
      
      expect(result).toBe('string-class array classes object-true conditional-true')
    })

    it('should preserve important modifiers', () => {
      const result = cn('!text-red-500', 'text-blue-500')
      expect(result).toBe('!text-red-500 text-blue-500')
    })

    it('should handle responsive and state modifiers', () => {
      const result = cn(
        'text-red-500',
        'sm:text-blue-500',
        'md:text-green-500',
        'hover:text-purple-500',
        'focus:text-yellow-500'
      )
      
      expect(result).toBe('text-red-500 sm:text-blue-500 md:text-green-500 hover:text-purple-500 focus:text-yellow-500')
    })

    it('should handle arbitrary values', () => {
      const result = cn(
        'text-[#1da1f2]',
        'bg-[rgb(255,0,0)]',
        'p-[17px]',
        'grid-cols-[1fr_2fr_1fr]'
      )
      
      expect(result).toBe('text-[#1da1f2] bg-[rgb(255,0,0)] p-[17px] grid-cols-[1fr_2fr_1fr]')
    })

    it('should work with CSS modules', () => {
      const styles = {
        button: 'button_abc123',
        active: 'active_def456'
      }
      
      const result = cn(styles.button, 'text-white', styles.active)
      expect(result).toBe('button_abc123 text-white active_def456')
    })

    it('should handle very long class strings', () => {
      const longClasses = Array(100).fill('class').map((c, i) => `${c}-${i}`).join(' ')
      const result = cn(longClasses)
      
      expect(result).toBeDefined()
      expect(result.split(' ').length).toBe(100)
    })

    it('should deduplicate identical classes', () => {
      const result = cn('text-red-500', 'text-red-500', 'text-red-500')
      expect(result).toBe('text-red-500')
    })

    it('should handle function returns', () => {
      const getClasses = () => 'dynamic-class'
      const result = cn('static-class', getClasses())
      expect(result).toBe('static-class dynamic-class')
    })

    it('should be pure function', () => {
      const input = ['text-red-500', 'bg-blue-500']
      const result1 = cn(...input)
      const result2 = cn(...input)
      
      expect(result1).toBe(result2)
      expect(input).toEqual(['text-red-500', 'bg-blue-500']) // Input not mutated
    })
  })
})