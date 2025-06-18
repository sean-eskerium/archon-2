import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Setup file for Vitest with React Testing Library
// This file is automatically loaded before each test 

// Mock scrollIntoView which is not available in jsdom
Element.prototype.scrollIntoView = vi.fn();

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
  }

  send = vi.fn()
  close = vi.fn()
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