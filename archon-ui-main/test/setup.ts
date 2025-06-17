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

// Replace global WebSocket with mock
(globalThis as any).WebSocket = MockWebSocket; 