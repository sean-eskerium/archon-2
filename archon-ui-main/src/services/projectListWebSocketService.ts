/**
 * Project List WebSocket Service
 * Handles real-time project list updates using EnhancedWebSocketService
 */

import {
  EnhancedWebSocketService,
  WebSocketState,
  WebSocketMessage,
  createWebSocketService
} from './EnhancedWebSocketService';

interface ProjectListCallbacks {
  onProjectCreated?: (project: any) => void;
  onProjectUpdated?: (project: any) => void;
  onProjectDeleted?: (project: any) => void;
  onProjectsUpdated?: (projects: any[]) => void;
  onError?: (error: Error) => void;
  onStateChange?: (state: WebSocketState) => void;
}

class ProjectListWebSocketService {
  private webSocketService: EnhancedWebSocketService | null = null;
  private callbacks: ProjectListCallbacks = {};

  async connect(callbacks: ProjectListCallbacks): Promise<void> {
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

      // Connect to project list endpoint
      const endpoint = '/api/projects/ws';
      await this.webSocketService.connect(endpoint);
      
      console.log('✅ Project list WebSocket connected');
    } catch (error) {
      console.error('Failed to connect project list WebSocket:', error);
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
      console.log(`📡 Project list WebSocket state changed: ${state}`);
      
      if (this.callbacks.onStateChange) {
        this.callbacks.onStateChange(state);
      }
    });

    // Handle errors
    this.webSocketService.addErrorHandler((error: Event | Error) => {
      console.error('Project list WebSocket error:', error);
      if (this.callbacks.onError) {
        this.callbacks.onError(error instanceof Error ? error : new Error('WebSocket error'));
      }
    });
  }

  private handleMessage(message: WebSocketMessage): void {
    console.log('📨 Project list update received:', message);

    switch (message.type) {
      case 'project_created':
        if (this.callbacks.onProjectCreated) {
          this.callbacks.onProjectCreated(message.data);
        }
        break;
        
      case 'project_updated':
        if (this.callbacks.onProjectUpdated) {
          this.callbacks.onProjectUpdated(message.data);
        }
        break;
        
      case 'project_deleted':
        if (this.callbacks.onProjectDeleted) {
          this.callbacks.onProjectDeleted(message.data);
        }
        break;
        
      case 'projects_updated':
        if (this.callbacks.onProjectsUpdated) {
          this.callbacks.onProjectsUpdated(message.data);
        }
        break;
        
      default:
        console.warn('Unknown project list message type:', message.type);
    }
  }

  send(data: any): boolean {
    if (this.webSocketService?.isConnected()) {
      return this.webSocketService.send(data);
    }
    return false;
  }

  async disconnect(): Promise<void> {
    console.log('🔌 Disconnecting Project list WebSocket');
    
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
export const projectListWebSocket = new ProjectListWebSocketService();