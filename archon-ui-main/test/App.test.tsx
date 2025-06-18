import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { KnowledgeBasePage } from '@/pages/KnowledgeBasePage'
import { knowledgeBaseService } from '@/services/knowledgeBaseService'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { ToastProvider } from '@/contexts/ToastContext'
import { SettingsProvider } from '@/contexts/SettingsContext'

// Clear mocks that might interfere
vi.unmock('@/contexts/ThemeContext');
vi.unmock('@/contexts/ToastContext');
vi.unmock('@/contexts/SettingsContext');

// Mock the knowledge base service
vi.mock('@/services/knowledgeBaseService')

describe('App Components', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock the service to return empty results
    ;(knowledgeBaseService.getKnowledgeItems as any).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 20
    })
  })

  it('renders KnowledgeBasePage without crashing', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <ToastProvider>
            <SettingsProvider>
              <KnowledgeBasePage />
            </SettingsProvider>
          </ToastProvider>
        </ThemeProvider>
      </MemoryRouter>
    )
    
    // Check that the page renders some content
    expect(document.body).toBeInTheDocument()
  })

  it('should display Knowledge Base heading', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <ToastProvider>
            <SettingsProvider>
              <KnowledgeBasePage />
            </SettingsProvider>
          </ToastProvider>
        </ThemeProvider>
      </MemoryRouter>
    )
    
    // Should render the Knowledge Base page content
    expect(screen.getByText('Knowledge Base')).toBeInTheDocument()
  })
}) 