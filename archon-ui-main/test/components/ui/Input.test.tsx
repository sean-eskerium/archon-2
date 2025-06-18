import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Input } from '@/components/ui/Input'

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

describe('Input', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Basic Functionality', () => {
    it('should accept text input', async () => {
      const user = userEvent.setup()
      render(<Input placeholder="Enter text" />)
      
      const input = screen.getByPlaceholderText('Enter text')
      await user.type(input, 'Hello world')
      
      expect(input).toHaveValue('Hello world')
    })

    it('should show placeholder', () => {
      render(<Input placeholder="Enter your name" />)
      
      const input = screen.getByPlaceholderText('Enter your name')
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('placeholder', 'Enter your name')
    })

    it('should be disabled when specified', () => {
      render(<Input disabled placeholder="Disabled input" />)
      
      const input = screen.getByPlaceholderText('Disabled input')
      expect(input).toBeDisabled()
    })

    it('should support different input types', () => {
      render(
        <>
          <Input type="email" placeholder="Email" />
          <Input type="password" placeholder="Password" />
          <Input type="number" placeholder="Number" />
        </>
      )
      
      expect(screen.getByPlaceholderText('Email')).toHaveAttribute('type', 'email')
      expect(screen.getByPlaceholderText('Password')).toHaveAttribute('type', 'password')
      expect(screen.getByPlaceholderText('Number')).toHaveAttribute('type', 'number')
    })
  })

  describe('Label Support', () => {
    it('should render label when provided', () => {
      render(<Input label="Username" placeholder="Enter username" />)
      
      expect(screen.getByText('Username')).toBeInTheDocument()
      const label = screen.getByText('Username')
      expect(label.tagName).toBe('LABEL')
      expect(label).toHaveClass('block', 'text-gray-600', 'text-sm')
    })

    it('should not render label when not provided', () => {
      render(<Input placeholder="No label" />)
      
      expect(screen.queryByRole('label')).not.toBeInTheDocument()
    })
  })

  describe('Icon Support', () => {
    it('should render icon when provided', () => {
      const TestIcon = () => <svg data-testid="test-icon">Icon</svg>
      
      render(
        <Input 
          icon={<TestIcon />}
          placeholder="Input with icon"
        />
      )
      
      expect(screen.getByTestId('test-icon')).toBeInTheDocument()
      const iconWrapper = screen.getByTestId('test-icon').parentElement
      expect(iconWrapper).toHaveClass('mr-2', 'text-gray-500')
    })

    it('should render icon before input', () => {
      const TestIcon = () => <span data-testid="icon">🔍</span>
      
      render(
        <Input 
          icon={<TestIcon />}
          placeholder="Search"
        />
      )
      
      const container = screen.getByPlaceholderText('Search').parentElement
      const children = Array.from(container!.children)
      
      // Icon wrapper should be first child
      expect(children[0]).toContainElement(screen.getByTestId('icon'))
      // Input should be second child
      expect(children[1]).toBe(screen.getByPlaceholderText('Search'))
    })
  })

  describe('Accent Colors', () => {
    it('should apply purple accent color by default', () => {
      render(<Input placeholder="Default purple" />)
      
      const container = screen.getByPlaceholderText('Default purple').parentElement
      expect(container).toHaveClass('focus-within:border-purple-500')
      expect(container).toHaveClass('focus-within:shadow-[0_0_15px_rgba(168,85,247,0.5)]')
    })

    it('should apply green accent color', () => {
      render(<Input accentColor="green" placeholder="Green accent" />)
      
      const container = screen.getByPlaceholderText('Green accent').parentElement
      expect(container).toHaveClass('focus-within:border-emerald-500')
      expect(container).toHaveClass('focus-within:shadow-[0_0_15px_rgba(16,185,129,0.5)]')
    })

    it('should apply pink accent color', () => {
      render(<Input accentColor="pink" placeholder="Pink accent" />)
      
      const container = screen.getByPlaceholderText('Pink accent').parentElement
      expect(container).toHaveClass('focus-within:border-pink-500')
      expect(container).toHaveClass('focus-within:shadow-[0_0_15px_rgba(236,72,153,0.5)]')
    })

    it('should apply blue accent color', () => {
      render(<Input accentColor="blue" placeholder="Blue accent" />)
      
      const container = screen.getByPlaceholderText('Blue accent').parentElement
      expect(container).toHaveClass('focus-within:border-blue-500')
      expect(container).toHaveClass('focus-within:shadow-[0_0_15px_rgba(59,130,246,0.5)]')
    })
  })

  describe('Event Handlers', () => {
    it('should handle onChange events', async () => {
      const user = userEvent.setup()
      const handleChange = vi.fn()
      
      render(<Input onChange={handleChange} placeholder="Change me" />)
      
      const input = screen.getByPlaceholderText('Change me')
      await user.type(input, 'a')
      
      expect(handleChange).toHaveBeenCalled()
    })

    it('should handle onFocus events', async () => {
      const user = userEvent.setup()
      const handleFocus = vi.fn()
      
      render(<Input onFocus={handleFocus} placeholder="Focus me" />)
      
      const input = screen.getByPlaceholderText('Focus me')
      await user.click(input)
      
      expect(handleFocus).toHaveBeenCalled()
    })

    it('should handle onBlur events', async () => {
      const user = userEvent.setup()
      const handleBlur = vi.fn()
      
      render(<Input onBlur={handleBlur} placeholder="Blur me" />)
      
      const input = screen.getByPlaceholderText('Blur me')
      await user.click(input)
      await user.tab() // Tab away to trigger blur
      
      expect(handleBlur).toHaveBeenCalled()
    })

    it('should handle onKeyDown events', async () => {
      const user = userEvent.setup()
      const handleKeyDown = vi.fn()
      
      render(<Input onKeyDown={handleKeyDown} placeholder="Type here" />)
      
      const input = screen.getByPlaceholderText('Type here')
      await user.type(input, '{Enter}')
      
      expect(handleKeyDown).toHaveBeenCalled()
    })
  })

  describe('HTML Attributes', () => {
    it('should forward HTML input attributes', () => {
      render(
        <Input 
          name="username"
          id="username-input"
          required
          minLength={3}
          maxLength={20}
          pattern="[a-zA-Z0-9]+"
          autoComplete="username"
          placeholder="Username"
        />
      )
      
      const input = screen.getByPlaceholderText('Username')
      expect(input).toHaveAttribute('name', 'username')
      expect(input).toHaveAttribute('id', 'username-input')
      expect(input).toHaveAttribute('required')
      expect(input).toHaveAttribute('minLength', '3')
      expect(input).toHaveAttribute('maxLength', '20')
      expect(input).toHaveAttribute('pattern', '[a-zA-Z0-9]+')
      expect(input).toHaveAttribute('autoComplete', 'username')
    })

    it('should support value prop', () => {
      render(<Input value="Controlled value" onChange={() => {}} />)
      
      const input = screen.getByDisplayValue('Controlled value')
      expect(input).toBeInTheDocument()
    })

    it('should support defaultValue prop', () => {
      render(<Input defaultValue="Default value" />)
      
      const input = screen.getByDisplayValue('Default value')
      expect(input).toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('should apply base container styles', () => {
      render(<Input placeholder="Styled input" />)
      
      const container = screen.getByPlaceholderText('Styled input').parentElement
      expect(container).toHaveClass('flex', 'items-center', 'backdrop-blur-md')
      expect(container).toHaveClass('bg-gradient-to-b', 'rounded-md')
      expect(container).toHaveClass('px-3', 'py-2')
      expect(container).toHaveClass('transition-all', 'duration-200')
    })

    it('should apply input styles', () => {
      render(<Input placeholder="Input styles" />)
      
      const input = screen.getByPlaceholderText('Input styles')
      expect(input).toHaveClass('w-full', 'bg-transparent')
      expect(input).toHaveClass('text-gray-800', 'placeholder:text-gray-400')
      expect(input).toHaveClass('focus:outline-none')
    })

    it('should accept custom className', () => {
      render(<Input className="text-xl font-bold" placeholder="Custom class" />)
      
      const input = screen.getByPlaceholderText('Custom class')
      expect(input).toHaveClass('text-xl', 'font-bold')
    })

    it('should merge custom className with default styles', () => {
      render(<Input className="text-red-500" placeholder="Merged styles" />)
      
      const input = screen.getByPlaceholderText('Merged styles')
      expect(input).toHaveClass('text-red-500')
      expect(input).toHaveClass('w-full') // Should still have default styles
    })
  })
})