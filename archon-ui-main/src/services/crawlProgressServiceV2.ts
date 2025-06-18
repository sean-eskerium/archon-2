/**
 * Crawl Progress Service V2
 * 
 * Refactored to use the EnhancedWebSocketService for better reliability,
 * connection management, and error handling.
 */

import { 
  EnhancedWebSocketService, 
  WebSocketState, 
  WebSocketMessage,
  createWebSocketService 
} from './EnhancedWebSocketService';

export interface ProgressStep {
  id: string;
  label: string;
  percentage: number;
  status: 'pending' | 'active' | 'completed' | 'error';
  message?: string;
}

export interface CrawlProgressData {
  progressId: string;
  status: 'starting' | 'crawling' | 'analyzing' | 'sitemap' | 'text_file' | 'webpage' | 'processing' | 'storing' | 'completed' | 'error' | 'waiting' | 'reading' | 'extracting' | 'chunking' | 'creating_source' | 'summarizing' | 'source_creation' | 'document_storage' | 'code_storage' | 'finalization';
  percentage: number;
  currentUrl?: string;
  eta?: string;
  totalPages?: number;
  processedPages?: number;
  chunksStored?: number;
  wordCount?: number;
  duration?: string;
  error?: string;
  log?: string;
  logs: string[];
  steps?: ProgressStep[];
  currentStep?: string;
  stepMessage?: string;
  uploadType?: 'document';
  fileName?: string;
  fileType?: string;
  sourceId?: string;
}

interface StreamProgressOptions {
  autoReconnect?: boolean;
  reconnectDelay?: number;
  connectionTimeout?: number;
}

type ProgressCallback = (data: CrawlProgressData) => void;
type ConnectionStateCallback = (state: WebSocketState) => void;
type ErrorCallback = (error: Error) => void;

interface ProgressHandler {
  progressId: string;
  onMessage: ProgressCallback;
  onStateChange?: ConnectionStateCallback;
  onError?: ErrorCallback;
}

class CrawlProgressServiceV2 {
  private progressHandlers: Map<string, ProgressHandler> = new Map();
  private webSocketService: EnhancedWebSocketService | null = null;
  private currentProgressId: string | null = null;

  /**
   * Stream crawl progress with enhanced connection management
   */
  async streamProgress(
    progressId: string,
    onMessage: ProgressCallback,
    options: StreamProgressOptions = {}
  ): Promise<void> {
    const {
      autoReconnect = true,
      reconnectDelay = 5000,
      connectionTimeout = 10000
    } = options;

    // Store the handler
    this.progressHandlers.set(progressId, {
      progressId,
      onMessage
    });

    // Create WebSocket service if needed
    if (!this.webSocketService) {
      this.webSocketService = createWebSocketService({
        enableAutoReconnect: autoReconnect,
        reconnectInterval: reconnectDelay,
        maxReconnectAttempts: 5,
        heartbeatInterval: 30000,
        messageTimeout: 65000,
        enableHeartbeat: true
      });

      // Set up message handlers
      this.setupMessageHandlers();
    }

    // Update current progress ID
    this.currentProgressId = progressId;

    try {
      // Connect to the progress endpoint
      const endpoint = `/api/crawl-progress/${progressId}`;
      await this.webSocketService.connect(endpoint);
      
      console.log(`✅ Connected to crawl progress stream: ${progressId}`);
    } catch (error) {
      console.error(`❌ Failed to connect to crawl progress stream: ${progressId}`, error);
      this.progressHandlers.delete(progressId);
      throw error;
    }
  }

  /**
   * Enhanced stream progress with callbacks for connection state and errors
   */
  async streamProgressEnhanced(
    progressId: string,
    callbacks: {
      onMessage: ProgressCallback;
      onStateChange?: ConnectionStateCallback;
      onError?: ErrorCallback;
    },
    options: StreamProgressOptions = {}
  ): Promise<void> {
    // Store the enhanced handler
    this.progressHandlers.set(progressId, {
      progressId,
      ...callbacks
    });

    // Add state change handler if provided
    if (callbacks.onStateChange && this.webSocketService) {
      this.webSocketService.addStateChangeHandler(callbacks.onStateChange);
    }

    // Add error handler if provided
    if (callbacks.onError && this.webSocketService) {
      this.webSocketService.addErrorHandler(callbacks.onError);
    }

    // Stream progress
    return this.streamProgress(progressId, callbacks.onMessage, options);
  }

  private setupMessageHandlers(): void {
    if (!this.webSocketService) return;

    // Handle crawl progress messages
    this.webSocketService.addMessageHandler('crawl_progress', (message: WebSocketMessage) => {
      this.handleProgressMessage(message);
    });

    // Handle crawl completed messages
    this.webSocketService.addMessageHandler('crawl_completed', (message: WebSocketMessage) => {
      this.handleProgressMessage(message);
    });

    // Handle crawl error messages
    this.webSocketService.addMessageHandler('crawl_error', (message: WebSocketMessage) => {
      this.handleProgressMessage(message);
    });

    // Handle connection state changes
    this.webSocketService.addStateChangeHandler((state: WebSocketState) => {
      console.log(`📡 Crawl progress WebSocket state changed: ${state}`);
      
      // Notify all handlers about state change
      this.progressHandlers.forEach(handler => {
        if (handler.onStateChange) {
          handler.onStateChange(state);
        }
      });
    });

    // Handle errors
    this.webSocketService.addErrorHandler((error: Event | Error) => {
      console.error('❌ Crawl progress WebSocket error:', error);
      
      // Notify all handlers about error
      this.progressHandlers.forEach(handler => {
        if (handler.onError) {
          handler.onError(error instanceof Error ? error : new Error('WebSocket error'));
        }
      });
    });
  }

  private handleProgressMessage(message: WebSocketMessage): void {
    // Ignore heartbeat messages
    if (message.type === 'ping' || message.type === 'pong' || message.type === 'heartbeat') {
      return;
    }

    // Extract progress data
    const data = message.data;
    if (!data || !data.progressId) {
      console.warn('⚠️ Received progress message without valid data:', message);
      return;
    }

    // Validate percentage
    if (typeof data.percentage !== 'number' || isNaN(data.percentage)) {
      data.percentage = 0;
    }

    // Find the handler for this progress ID
    const handler = this.progressHandlers.get(data.progressId);
    if (handler) {
      handler.onMessage(data);
    } else {
      console.warn(`⚠️ No handler found for progress ID: ${data.progressId}`);
    }

    // Handle completion and errors
    if (message.type === 'crawl_completed' || data.status === 'completed') {
      console.log(`✅ Crawl completed for progress ID: ${data.progressId}`);
      this.cleanupProgress(data.progressId);
    } else if (message.type === 'crawl_error' || data.status === 'error') {
      console.error(`❌ Crawl error for progress ID: ${data.progressId}`, data.error);
      this.cleanupProgress(data.progressId);
    }
  }

  /**
   * Wait for WebSocket connection to be established
   */
  async waitForConnection(timeout: number = 10000): Promise<void> {
    if (!this.webSocketService) {
      throw new Error('WebSocket service not initialized');
    }
    return this.webSocketService.waitForConnection(timeout);
  }

  /**
   * Get current connection state
   */
  getConnectionState(): WebSocketState {
    return this.webSocketService?.state || WebSocketState.DISCONNECTED;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.webSocketService?.isConnected() || false;
  }

  /**
   * Disconnect from a specific progress stream
   */
  disconnectProgress(progressId: string): void {
    this.cleanupProgress(progressId);
    
    // If this was the current progress and no other handlers, disconnect WebSocket
    if (progressId === this.currentProgressId && this.progressHandlers.size === 0) {
      this.disconnect();
    }
  }

  /**
   * Disconnect from all progress streams
   */
  disconnect(): void {
    if (this.webSocketService) {
      this.webSocketService.disconnect();
      this.webSocketService = null;
    }
    
    this.progressHandlers.clear();
    this.currentProgressId = null;
  }

  private cleanupProgress(progressId: string): void {
    const handler = this.progressHandlers.get(progressId);
    if (handler) {
      // Remove state change handler if it exists
      if (handler.onStateChange && this.webSocketService) {
        this.webSocketService.removeStateChangeHandler(handler.onStateChange);
      }
      
      // Remove error handler if it exists
      if (handler.onError && this.webSocketService) {
        this.webSocketService.removeErrorHandler(handler.onError);
      }
      
      // Remove from handlers map
      this.progressHandlers.delete(progressId);
    }
  }

  // Backward compatibility methods
  connect(_progressId: string): void {
    console.warn('crawlProgressService.connect() is deprecated. Use streamProgress() instead.');
  }

  onProgress(_callback: ProgressCallback): void {
    console.warn('crawlProgressService.onProgress() is deprecated. Pass callback to streamProgress() instead.');
  }

  onCompleted(_callback: ProgressCallback): void {
    console.warn('crawlProgressService.onCompleted() is deprecated. Pass callback to streamProgress() instead.');
  }

  onError(_callback: (error: Error) => void): void {
    console.warn('crawlProgressService.onError() is deprecated. Use streamProgressEnhanced() instead.');
  }

  removeProgressCallback(_callback: ProgressCallback): void {
    // No-op for backward compatibility
  }

  removeErrorCallback(_callback: (error: Error) => void): void {
    // No-op for backward compatibility
  }
}

// Export singleton instance
export const crawlProgressServiceV2 = new CrawlProgressServiceV2();

// Also export the types for external use
export type { ProgressCallback, ConnectionStateCallback, ErrorCallback };