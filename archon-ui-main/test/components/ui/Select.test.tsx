import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Select } from '@/components/ui/Select'

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

describe('Select', () => {
  const defaultOptions = [
    { value: 'option1', label: 'Option 1' },
    { value: 'option2', label: 'Option 2' },
    { value: 'option3', label: 'Option 3' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Basic Functionality', () => {
    it('should display options', () => {
      render(<Select options={defaultOptions} />)
      
      expect(screen.getByRole('option', { name: 'Option 1' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Option 2' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Option 3' })).toBeInTheDocument()
    })

    it('should handle selection', async () => {
      const user = userEvent.setup()
      const handleChange = vi.fn()
      
      render(<Select options={defaultOptions} onChange={handleChange} />)
      
      const select = screen.getByRole('combobox')
      await user.selectOptions(select, 'option2')
      
      expect(handleChange).toHaveBeenCalled()
      expect(select).toHaveValue('option2')
    })

    it('should render with default value', () => {
      render(<Select options={defaultOptions} defaultValue="option2" />)
      
      const select = screen.getByRole('combobox')
      expect(select).toHaveValue('option2')
    })

    it('should be disabled when specified', () => {
      render(<Select options={defaultOptions} disabled />)
      
      const select = screen.getByRole('combobox')
      expect(select).toBeDisabled()
    })
  })

  describe('Label Support', () => {
    it('should render label when provided', () => {
      render(<Select options={defaultOptions} label="Choose an option" />)
      
      expect(screen.getByText('Choose an option')).toBeInTheDocument()
      const label = screen.getByText('Choose an option')
      expect(label.tagName).toBe('LABEL')
      expect(label).toHaveClass('block', 'text-gray-600', 'text-sm')
    })

    it('should not render label when not provided', () => {
      render(<Select options={defaultOptions} />)
      
      expect(screen.queryByRole('label')).not.toBeInTheDocument()
    })
  })

  describe('Accent Colors', () => {
    it('should apply purple accent color by default', () => {
      render(<Select options={defaultOptions} />)
      
      const container = screen.getByRole('combobox').parentElement
      expect(container).toHaveClass('focus-within:border-purple-500')
      expect(container).toHaveClass('focus-within:shadow-[0_0_15px_rgba(168,85,247,0.5)]')
    })

    it('should apply green accent color', () => {
      render(<Select options={defaultOptions} accentColor="green" />)
      
      const container = screen.getByRole('combobox').parentElement
      expect(container).toHaveClass('focus-within:border-emerald-500')
      expect(container).toHaveClass('focus-within:shadow-[0_0_15px_rgba(16,185,129,0.5)]')
    })

    it('should apply pink accent color', () => {
      render(<Select options={defaultOptions} accentColor="pink" />)
      
      const container = screen.getByRole('combobox').parentElement
      expect(container).toHaveClass('focus-within:border-pink-500')
      expect(container).toHaveClass('focus-within:shadow-[0_0_15px_rgba(236,72,153,0.5)]')
    })

    it('should apply blue accent color', () => {
      render(<Select options={defaultOptions} accentColor="blue" />)
      
      const container = screen.getByRole('combobox').parentElement
      expect(container).toHaveClass('focus-within:border-blue-500')
      expect(container).toHaveClass('focus-within:shadow-[0_0_15px_rgba(59,130,246,0.5)]')
    })
  })

  describe('Options Handling', () => {
    it('should handle empty options array', () => {
      render(<Select options={[]} />)
      
      const select = screen.getByRole('combobox')
      expect(select.children.length).toBe(0)
    })

    it('should handle many options', () => {
      const manyOptions = Array.from({ length: 50 }, (_, i) => ({
        value: `opt${i}`,
        label: `Option ${i + 1}`
      }))
      
      render(<Select options={manyOptions} />)
      
      const select = screen.getByRole('combobox')
      expect(select.children.length).toBe(50)
    })

    it('should render option values correctly', () => {
      const specialOptions = [
        { value: 'val-1', label: 'First Option' },
        { value: 'val-2', label: 'Second Option' }
      ]
      
      render(<Select options={specialOptions} />)
      
      const option1 = screen.getByRole('option', { name: 'First Option' }) as HTMLOptionElement
      const option2 = screen.getByRole('option', { name: 'Second Option' }) as HTMLOptionElement
      
      expect(option1.value).toBe('val-1')
      expect(option2.value).toBe('val-2')
    })
  })

  describe('HTML Attributes', () => {
    it('should forward HTML select attributes', () => {
      render(
        <Select 
          options={defaultOptions}
          name="select-field"
          id="select-id"
          required
          form="test-form"
        />
      )
      
      const select = screen.getByRole('combobox')
      expect(select).toHaveAttribute('name', 'select-field')
      expect(select).toHaveAttribute('id', 'select-id')
      expect(select).toHaveAttribute('required')
      expect(select).toHaveAttribute('form', 'test-form')
    })

    it('should support value prop for controlled component', () => {
      const { rerender } = render(
        <Select options={defaultOptions} value="option1" onChange={() => {}} />
      )
      
      expect(screen.getByRole('combobox')).toHaveValue('option1')
      
      rerender(
        <Select options={defaultOptions} value="option3" onChange={() => {}} />
      )
      
      expect(screen.getByRole('combobox')).toHaveValue('option3')
    })
  })

  describe('Styling', () => {
    it('should apply base container styles', () => {
      render(<Select options={defaultOptions} />)
      
      const container = screen.getByRole('combobox').parentElement
      expect(container).toHaveClass('relative', 'backdrop-blur-md', 'bg-gradient-to-b')
      expect(container).toHaveClass('border', 'rounded-md')
      expect(container).toHaveClass('transition-all', 'duration-200')
    })

    it('should apply select styles', () => {
      render(<Select options={defaultOptions} />)
      
      const select = screen.getByRole('combobox')
      expect(select).toHaveClass('w-full', 'bg-transparent', 'appearance-none')
      expect(select).toHaveClass('px-3', 'py-2', 'focus:outline-none')
    })

    it('should render dropdown icon', () => {
      render(<Select options={defaultOptions} />)
      
      const icon = document.querySelector('svg')
      expect(icon).toBeInTheDocument()
      expect(icon?.parentElement).toHaveClass('absolute', 'right-3', 'pointer-events-none')
    })

    it('should accept custom className', () => {
      render(<Select options={defaultOptions} className="custom-select text-lg" />)
      
      const select = screen.getByRole('combobox')
      expect(select).toHaveClass('custom-select', 'text-lg')
    })
  })

  describe('Event Handlers', () => {
    it('should handle onFocus events', async () => {
      const user = userEvent.setup()
      const handleFocus = vi.fn()
      
      render(<Select options={defaultOptions} onFocus={handleFocus} />)
      
      await user.click(screen.getByRole('combobox'))
      
      expect(handleFocus).toHaveBeenCalled()
    })

    it('should handle onBlur events', async () => {
      const user = userEvent.setup()
      const handleBlur = vi.fn()
      
      render(<Select options={defaultOptions} onBlur={handleBlur} />)
      
      const select = screen.getByRole('combobox')
      await user.click(select)
      await user.tab() // Tab away to trigger blur
      
      expect(handleBlur).toHaveBeenCalled()
    })
  })
})