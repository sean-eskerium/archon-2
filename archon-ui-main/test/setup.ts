import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'
import React from 'react'

// Setup file for Vitest with React Testing Library
// This file is automatically loaded before each test 

// Clean up after each test - Following documented standards
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

// Mock scrollIntoView which is not available in jsdom
Element.prototype.scrollIntoView = vi.fn();

// Mock lucide-react using manual mock file
vi.mock('lucide-react')

// Mock WebSocket for tests
export class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  url: string
  readyState: number = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null

  constructor(url: string) {
    this.url = url
    // Simulate connection opening asynchronously
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) {
        this.onopen(new Event('open'))
      }
    }, 0)
  }

  send = vi.fn()
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close'))
    }
  })
}

// Create a properly mocked WebSocket constructor
const WebSocketMock = vi.fn().mockImplementation((url: string) => {
  return new MockWebSocket(url)
})

// Copy static properties
Object.assign(WebSocketMock, {
  CONNECTING: MockWebSocket.CONNECTING,
  OPEN: MockWebSocket.OPEN,
  CLOSING: MockWebSocket.CLOSING,
  CLOSED: MockWebSocket.CLOSED
})

// Replace global WebSocket with mock
global.WebSocket = WebSocketMock as any

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn()
}
global.localStorage = localStorageMock as any

// Mock sessionStorage
global.sessionStorage = localStorageMock as any

// Mock crypto for UUID generation (handle both browser and Node environments)
if (!global.crypto) {
  // @ts-ignore
  global.crypto = {}
}
Object.defineProperty(global.crypto, 'randomUUID', {
  value: vi.fn(() => 'test-uuid-' + Math.random().toString(36).substring(7)),
  writable: true,
  configurable: true
})

// Mock fetch for API calls
global.fetch = vi.fn()

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock HTMLCanvasElement.getContext
HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue(null)

// Mock URL.createObjectURL
global.URL.createObjectURL = vi.fn()
global.URL.revokeObjectURL = vi.fn()

// Mock EnhancedWebSocketService first
vi.mock('@/services/EnhancedWebSocketService', () => {
  const WebSocketState = {
    CONNECTING: 'CONNECTING',
    CONNECTED: 'CONNECTED',
    RECONNECTING: 'RECONNECTING',
    DISCONNECTED: 'DISCONNECTED',
    FAILED: 'FAILED'
  }

  class MockEnhancedWebSocketService {
    state = WebSocketState.DISCONNECTED
    
    connect = vi.fn().mockResolvedValue(undefined)
    disconnect = vi.fn()
    send = vi.fn().mockReturnValue(true)
    isConnected = vi.fn().mockReturnValue(true)
    waitForConnection = vi.fn().mockResolvedValue(undefined)
    addMessageHandler = vi.fn()
    removeMessageHandler = vi.fn()
    addErrorHandler = vi.fn()
    removeErrorHandler = vi.fn()
    addStateChangeHandler = vi.fn()
    removeStateChangeHandler = vi.fn()
  }

  return {
    EnhancedWebSocketService: MockEnhancedWebSocketService,
    createWebSocketService: vi.fn(() => new MockEnhancedWebSocketService()),
    WebSocketState
  }
})

// Enhanced WebSocket service mock - Following documented standards
vi.mock('@/services/websocketService', () => {
  const createMockWebSocketService = () => ({
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    subscribe: vi.fn().mockReturnValue(vi.fn()), // Returns unsubscribe function
    send: vi.fn(),
    getConnectionState: vi.fn().mockReturnValue('connected'),
    waitForConnection: vi.fn().mockResolvedValue(undefined),
    isConnected: vi.fn().mockReturnValue(true),
    reconnect: vi.fn().mockResolvedValue(undefined),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn()
  })

  const createMockTaskUpdateService = () => ({
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    sendPing: vi.fn(),
    isConnected: vi.fn().mockReturnValue(true)
  })

  // Mock WebSocketService class that matches the documented pattern
  class MockWebSocketService {
    enhancedService = {
      connect: vi.fn().mockResolvedValue(undefined),
      disconnect: vi.fn(),
      send: vi.fn().mockReturnValue(true),
      isConnected: vi.fn().mockReturnValue(true),
      waitForConnection: vi.fn().mockResolvedValue(undefined),
      addMessageHandler: vi.fn(),
      removeMessageHandler: vi.fn(),
      addErrorHandler: vi.fn(),
      removeErrorHandler: vi.fn(),
      addStateChangeHandler: vi.fn(),
      removeStateChangeHandler: vi.fn(),
      state: 'CONNECTED'
    }
    
    connect = vi.fn().mockResolvedValue(undefined)
    disconnect = vi.fn()
    subscribe = vi.fn().mockReturnValue(vi.fn())
    send = vi.fn()
    getConnectionState = vi.fn().mockReturnValue('connected')
    waitForConnection = vi.fn().mockResolvedValue(undefined)
    isConnected = vi.fn().mockReturnValue(true)
    reconnect = vi.fn().mockResolvedValue(undefined)
    addEventListener = vi.fn()
    removeEventListener = vi.fn()
  }

  return {
    // Main service  
    websocketService: createMockWebSocketService(),
    
    // Service class
    WebSocketService: MockWebSocketService,
    
    // Singleton instances
    knowledgeWebSocket: createMockWebSocketService(),
    crawlWebSocket: createMockWebSocketService(),
    projectListWebSocket: createMockWebSocketService(),
    healthWebSocket: createMockWebSocketService(),
    taskUpdateWebSocket: createMockTaskUpdateService(),
  }
})

// Mock agent chat service
vi.mock('@/services/agentChatService', () => ({
  agentChatService: {
    createSession: vi.fn().mockResolvedValue({ session_id: 'test-session-id' }),
    getSession: vi.fn().mockResolvedValue({ 
      session_id: 'test-session-id',
      messages: [],
      agent_type: 'rag',
      created_at: new Date()
    }),
    sendMessage: vi.fn().mockResolvedValue(undefined),
    connectWebSocket: vi.fn().mockResolvedValue(undefined),
    disconnectWebSocket: vi.fn(),
    isConnected: vi.fn().mockReturnValue(true),
    onStatusChange: vi.fn(),
    offStatusChange: vi.fn(),
    manualReconnect: vi.fn().mockResolvedValue(true)
  },
  ChatMessage: class {},
  ChatSession: class {},
  ChatRequest: class {}
}))

// Mock test service for better test isolation
vi.mock('@/services/testService', () => ({
  testService: {
    runTests: vi.fn().mockReturnValue({
      unsubscribe: vi.fn()
    }),
    disconnectAllStreams: vi.fn(),
    cancelTest: vi.fn()
  }
}))

// Console methods mock to reduce noise in test output
global.console = {
  ...console,
  log: vi.fn(),
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn()
}

// Enhanced Toast Context mock
const mockShowToast = vi.fn()
const mockHideToast = vi.fn()

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showToast: mockShowToast,
    hideToast: mockHideToast,
    toasts: []
  }),
  ToastProvider: ({ children }: { children: React.ReactNode }) => children
}))

// Make the mock functions available globally for tests
Object.assign(globalThis, {
  mockShowToast,
  mockHideToast,
  showToast: mockShowToast,  // Some tests might use showToast directly
  hideToast: mockHideToast   // Some tests might use hideToast directly
})

// Mock Theme Context  
vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    setTheme: vi.fn(),
    toggleTheme: vi.fn()
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children
}))

// Mock Settings Context - Following actual interface
vi.mock('@/contexts/SettingsContext', () => ({
  useSettings: () => ({
    projectsEnabled: true,
    setProjectsEnabled: vi.fn(),
    loading: false,
    refreshSettings: vi.fn().mockResolvedValue(undefined)
  }),
  SettingsProvider: ({ children }: { children: React.ReactNode }) => React.createElement(React.Fragment, null, children)
}))

// Mock KnowledgeTable component
vi.mock('@/components/knowledge-base/KnowledgeTable', () => ({
  KnowledgeTable: vi.fn(({ items, isLoading, onDelete, onTest }: any) => (
    React.createElement('div', { 'data-testid': 'knowledge-table' },
      isLoading && React.createElement('div', null, 'Loading...'),
      items?.map((item: any) => 
        React.createElement('div', { key: item.id, 'data-testid': `knowledge-item-${item.id}` },
          React.createElement('span', null, item.title),
          React.createElement('button', { onClick: () => onDelete?.(item.id) }, 'Delete'),
          React.createElement('button', { onClick: () => onTest?.(item.id) }, 'Test')
        )
      )
    )
  ))
}))

// All mocks are already set up above 