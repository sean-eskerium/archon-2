import { crawlProgressServiceV2 } from '../crawlProgressServiceV2';
import { WebSocketState } from '../EnhancedWebSocketService';
import { CrawlProgressData } from '../crawlProgressServiceV2';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {
    // Simulate connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(data: string): void {
    console.log('MockWebSocket send:', data);
  }

  close(code?: number, reason?: string): void {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }));
    }
  }
}

// Replace global WebSocket with mock
(global as any).WebSocket = MockWebSocket;

describe('CrawlProgressServiceV2', () => {
  beforeEach(() => {
    // Disconnect any existing connections
    crawlProgressServiceV2.disconnect();
  });

  afterEach(() => {
    // Clean up
    crawlProgressServiceV2.disconnect();
  });

  test('should connect to progress endpoint', async () => {
    const progressId = 'test-progress-123';
    let messageReceived = false;

    const onMessage = (data: CrawlProgressData) => {
      messageReceived = true;
      expect(data.progressId).toBe(progressId);
    };

    await crawlProgressServiceV2.streamProgress(progressId, onMessage);

    // Verify connection state
    expect(crawlProgressServiceV2.isConnected()).toBe(true);
    expect(crawlProgressServiceV2.getConnectionState()).toBe(WebSocketState.CONNECTED);
  });

  test('should handle progress messages', async () => {
    const progressId = 'test-progress-456';
    const messages: CrawlProgressData[] = [];

    await crawlProgressServiceV2.streamProgress(progressId, (data) => {
      messages.push(data);
    });

    // Simulate receiving a progress message
    const mockWs = (global as any).WebSocket.prototype;
    const progressMessage = {
      type: 'crawl_progress',
      data: {
        progressId,
        status: 'crawling',
        percentage: 50,
        log: 'Crawling in progress...'
      }
    };

    // Wait for connection
    await new Promise(resolve => setTimeout(resolve, 150));

    // Send mock message
    if (mockWs.onmessage) {
      mockWs.onmessage(new MessageEvent('message', {
        data: JSON.stringify(progressMessage)
      }));
    }

    // Verify message was handled
    expect(messages.length).toBe(1);
    expect(messages[0].status).toBe('crawling');
    expect(messages[0].percentage).toBe(50);
  });

  test('should handle connection state changes', async () => {
    const progressId = 'test-progress-789';
    const stateChanges: WebSocketState[] = [];

    await crawlProgressServiceV2.streamProgressEnhanced(progressId, {
      onMessage: () => {},
      onStateChange: (state) => {
        stateChanges.push(state);
      }
    });

    // Wait for connection
    await new Promise(resolve => setTimeout(resolve, 150));

    // Should have received CONNECTING and CONNECTED states
    expect(stateChanges).toContain(WebSocketState.CONNECTING);
    expect(stateChanges).toContain(WebSocketState.CONNECTED);
  });

  test('should clean up on disconnect', async () => {
    const progressId = 'test-progress-cleanup';

    await crawlProgressServiceV2.streamProgress(progressId, () => {});
    
    // Wait for connection
    await new Promise(resolve => setTimeout(resolve, 150));
    
    expect(crawlProgressServiceV2.isConnected()).toBe(true);

    // Disconnect specific progress
    crawlProgressServiceV2.disconnectProgress(progressId);

    // Since it's the only connection, should disconnect WebSocket
    expect(crawlProgressServiceV2.isConnected()).toBe(false);
  });

  test('should handle errors gracefully', async () => {
    const progressId = 'test-progress-error';
    let errorReceived = false;

    await crawlProgressServiceV2.streamProgressEnhanced(progressId, {
      onMessage: () => {},
      onError: (error) => {
        errorReceived = true;
        expect(error).toBeInstanceOf(Error);
      }
    });

    // Simulate an error
    const mockWs = (global as any).WebSocket.prototype;
    if (mockWs.onerror) {
      mockWs.onerror(new Event('error'));
    }

    expect(errorReceived).toBe(true);
  });
});