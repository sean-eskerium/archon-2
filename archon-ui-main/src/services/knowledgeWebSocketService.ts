/**
 * Knowledge WebSocket Service
 * Handles real-time knowledge base updates using EnhancedWebSocketService
 */

import {
  EnhancedWebSocketService,
  WebSocketState,
  WebSocketMessage,
  createWebSocketService
} from './EnhancedWebSocketService';

interface KnowledgeUpdateCallbacks {
  onSourceUpdate?: (data: any) => void;
  onKnowledgeUpdate?: (data: any) => void;
  onError?: (error: Error) => void;
  onStateChange?: (state: WebSocketState) => void;
}

class KnowledgeWebSocketService {
  private webSocketService: EnhancedWebSocketService | null = null;
  private callbacks: KnowledgeUpdateCallbacks = {};

  async connect(callbacks: KnowledgeUpdateCallbacks): Promise<void> {
    this.callbacks = callbacks;

    try {
      // Create WebSocket service if needed
      if (!this.webSocketService) {
        this.webSocketService = createWebSocketService({
          enableAutoReconnect: true,
          maxReconnectAttempts: 5,
          reconnectInterval: 1000,
          heartbeatInterval: 30000,
          enableHeartbeat: true
        });

        this.setupHandlers();
      }

      // Connect to knowledge endpoint
      const endpoint = '/api/knowledge/ws';
      await this.webSocketService.connect(endpoint);
      
      console.log('✅ Knowledge WebSocket connected');
    } catch (error) {
      console.error('Failed to connect knowledge WebSocket:', error);
      throw error;
    }
  }

  private setupHandlers(): void {
    if (!this.webSocketService) return;

    // Handle different message types
    this.webSocketService.addMessageHandler('*', (message: WebSocketMessage) => {
      this.handleMessage(message);
    });

    // Handle connection state changes
    this.webSocketService.addStateChangeHandler((state: WebSocketState) => {
      console.log(`📡 Knowledge WebSocket state changed: ${state}`);
      
      if (this.callbacks.onStateChange) {
        this.callbacks.onStateChange(state);
      }
    });

    // Handle errors
    this.webSocketService.addErrorHandler((error: Event | Error) => {
      console.error('Knowledge WebSocket error:', error);
      if (this.callbacks.onError) {
        this.callbacks.onError(error instanceof Error ? error : new Error('WebSocket error'));
      }
    });
  }

  private handleMessage(message: WebSocketMessage): void {
    console.log('📨 Knowledge update received:', message);

    switch (message.type) {
      case 'source_update':
        if (this.callbacks.onSourceUpdate) {
          this.callbacks.onSourceUpdate(message.data);
        }
        break;
        
      case 'knowledge_update':
        if (this.callbacks.onKnowledgeUpdate) {
          this.callbacks.onKnowledgeUpdate(message.data);
        }
        break;
        
      default:
        console.warn('Unknown knowledge message type:', message.type);
    }
  }

  send(data: any): boolean {
    if (this.webSocketService?.isConnected()) {
      return this.webSocketService.send(data);
    }
    return false;
  }

  async disconnect(): Promise<void> {
    console.log('🔌 Disconnecting Knowledge WebSocket');
    
    if (this.webSocketService) {
      this.webSocketService.disconnect();
      this.webSocketService = null;
    }
    
    this.callbacks = {};
  }

  isConnected(): boolean {
    return this.webSocketService?.isConnected() || false;
  }

  getConnectionState(): WebSocketState {
    return this.webSocketService?.state || WebSocketState.DISCONNECTED;
  }
}

// Export singleton instance
export const knowledgeWebSocket = new KnowledgeWebSocketService();