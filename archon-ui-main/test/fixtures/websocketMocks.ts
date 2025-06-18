import { vi } from 'vitest'

export const createMockWebSocketService = () => ({
  connect: vi.fn(),
  disconnect: vi.fn(),
  subscribe: vi.fn((channel, callback) => {
    // Return unsubscribe function
    return vi.fn()
  }),
  send: vi.fn(),
  getConnectionState: vi.fn(() => 'connected'),
  waitForConnection: vi.fn(() => Promise.resolve()),
})

export const mockWebSocketMessages = {
  projectUpdate: {
    type: 'project.update',
    data: {
      id: '1',
      title: 'Updated Project',
      updated_at: new Date().toISOString()
    }
  },
  taskCreated: {
    type: 'task.created',
    data: {
      id: '3',
      title: 'New Task',
      project_id: '1'
    }
  },
  crawlProgress: {
    type: 'crawl.progress',
    data: {
      url: 'https://example.com',
      pages_crawled: 10,
      total_pages: 50,
      status: 'crawling'
    }
  },
  error: {
    type: 'error',
    data: {
      message: 'Something went wrong',
      code: 'INTERNAL_ERROR'
    }
  }
}

export const simulateWebSocketMessage = (
  mockSubscribe: any,
  message: any,
  delay = 0
) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const callback = mockSubscribe.mock.calls[0][1]
      callback(message)
      resolve(message)
    }, delay)
  })
}