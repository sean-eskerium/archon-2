import React from 'react'
import { render as rtlRender } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { ToastProvider } from '@/contexts/ToastContext'
import { SettingsProvider } from '@/contexts/SettingsContext'

interface WrapperProps {
  children: React.ReactNode
}

function AllTheProviders({ children }: WrapperProps) {
  return (
    <MemoryRouter>
      <ThemeProvider>
        <ToastProvider>
          <SettingsProvider>
            {children}
          </SettingsProvider>
        </ToastProvider>
      </ThemeProvider>
    </MemoryRouter>
  )
}

export function renderWithProviders(
  ui: React.ReactElement,
  options = {}
) {
  return rtlRender(ui, {
    wrapper: AllTheProviders,
    ...options
  })
}

// Re-export everything
export * from '@testing-library/react'
export { renderWithProviders as render }