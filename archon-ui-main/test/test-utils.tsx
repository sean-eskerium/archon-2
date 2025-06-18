import React from 'react'
import { vi } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { ToastProvider } from '@/contexts/ToastContext'
import { SettingsProvider } from '@/contexts/SettingsContext'

// Mock functions that can be reused
export const mockShowToast = vi.fn()
export const mockHideToast = vi.fn()

// Test wrapper with all providers
export const AllProviders = ({ children }: { children: React.ReactNode }) => (
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

// Custom render with all providers
export const renderWithProviders = (ui: React.ReactElement, options = {}) => {
  return render(ui, { wrapper: AllProviders, ...options })
}

// Common mock responses
export const mockKnowledgeItems = {
  items: [],
  total: 0,
  page: 1,
  per_page: 20
}

export const mockProject = {
  id: 'test-project-id',
  title: 'Test Project',
  description: 'Test Description',
  icon: '🚀',
  color: 'blue',
  pinned: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
}

export const mockTask = {
  id: 'test-task-id',
  project_id: 'test-project-id',
  title: 'Test Task',
  description: 'Test Description',
  status: 'todo',
  priority: 'medium',
  assignee: 'User',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
}

// Mock WebSocket message
export const createMockWebSocketMessage = (data: any) => {
  return new MessageEvent('message', {
    data: JSON.stringify(data)
  })
}

// Mock all services with default implementations
export const setupServiceMocks = () => {
  // Knowledge Base Service
  vi.mock('@/services/knowledgeBaseService', () => ({
    knowledgeBaseService: {
      getKnowledgeItems: vi.fn().mockResolvedValue(mockKnowledgeItems),
      crawlUrl: vi.fn().mockResolvedValue({ success: true }),
      uploadFile: vi.fn().mockResolvedValue({ success: true }),
      deleteKnowledgeItem: vi.fn().mockResolvedValue({ success: true }),
      testKnowledgeItem: vi.fn().mockResolvedValue({ success: true })
    }
  }))

  // Project Service
  vi.mock('@/services/projectService', () => ({
    projectService: {
      listProjects: vi.fn().mockResolvedValue([mockProject]),
      getProject: vi.fn().mockResolvedValue(mockProject),
      createProject: vi.fn().mockResolvedValue(mockProject),
      updateProject: vi.fn().mockResolvedValue(mockProject),
      deleteProject: vi.fn().mockResolvedValue({ success: true }),
      listTasks: vi.fn().mockResolvedValue([mockTask]),
      createTask: vi.fn().mockResolvedValue(mockTask),
      updateTask: vi.fn().mockResolvedValue(mockTask),
      updateTaskStatus: vi.fn().mockResolvedValue(mockTask),
      deleteTask: vi.fn().mockResolvedValue({ success: true }),
      subscribeToProjectUpdates: vi.fn().mockReturnValue(() => {})
    }
  }))

  // API Service
  vi.mock('@/services/api', () => ({
    performRAGQuery: vi.fn().mockResolvedValue({ answer: 'Test answer' }),
    getSettings: vi.fn().mockResolvedValue({}),
    updateSettings: vi.fn().mockResolvedValue({})
  }))

  // Credentials Service
  vi.mock('@/services/credentialsService', () => ({
    credentialsService: {
      getCredential: vi.fn().mockResolvedValue({ value: 'test-value' }),
      createCredential: vi.fn().mockResolvedValue({ success: true }),
      updateCredential: vi.fn().mockResolvedValue({ success: true }),
      deleteCredential: vi.fn().mockResolvedValue({ success: true }),
      listCredentials: vi.fn().mockResolvedValue([])
    }
  }))
}

// Setup all component mocks
export const setupComponentMocks = () => {
  // Mock problematic components
  vi.mock('@/components/animations/Animations', () => ({
    default: () => null,
    Animations: () => null
  }))

  vi.mock('@/components/CrawlingProgressCard', () => ({
    CrawlingProgressCard: ({ onClose }: any) => (
      <div data-testid="crawling-progress-card">
        <button onClick={onClose}>Close</button>
      </div>
    )
  }))

  vi.mock('@/components/ui/GlassCrawlDepthSelector', () => ({
    GlassCrawlDepthSelector: ({ value, onChange }: any) => (
      <select 
        data-testid="crawl-depth-selector" 
        value={value} 
        onChange={(e) => onChange(Number(e.target.value))}
      >
        <option value="1">1</option>
        <option value="2">2</option>
        <option value="3">3</option>
      </select>
    )
  }))
}

// Clear all mocks utility
export const clearAllMocks = () => {
  vi.clearAllMocks()
  vi.resetModules()
}