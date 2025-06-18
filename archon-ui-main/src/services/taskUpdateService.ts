/**
 * Task Update Service
 * Handles real-time task updates using EnhancedWebSocketService
 */

import {
  EnhancedWebSocketService,
  WebSocketState,
  WebSocketMessage,
  createWebSocketService
} from './EnhancedWebSocketService';

interface TaskUpdateData {
  type: 'task_created' | 'task_updated' | 'task_deleted' | 'task_archived' | 'connection_established' | 'initial_tasks' | 'tasks_updated' | 'heartbeat' | 'pong';
  data: any;
  timestamp: string;
  project_id: string;
}

interface TaskUpdateCallbacks {
  onTaskCreated?: (task: any) => void;
  onTaskUpdated?: (task: any) => void;
  onTaskDeleted?: (task: any) => void;
  onTaskArchived?: (task: any) => void;
  onConnectionEstablished?: () => void;
  onInitialTasks?: (tasks: any[]) => void;
  onTasksChange?: (tasks: any[]) => void;
  onError?: (error: Error) => void;
  onClose?: () => void;
  onStateChange?: (state: WebSocketState) => void;
}

class TaskUpdateService {
  private webSocketService: EnhancedWebSocketService | null = null;
  private projectId: string | null = null;
  private sessionId: string | null = null;
  private callbacks: TaskUpdateCallbacks = {};
  private isConnecting = false;

  async connect(projectId: string, callbacks: TaskUpdateCallbacks, sessionId?: string): Promise<void> {
    // If already connected to the same project, just update callbacks
    if (this.projectId === projectId && this.webSocketService?.isConnected()) {
      console.log('🔄 Already connected to project, updating callbacks');
      this.callbacks = callbacks;
      return;
    }

    // Disconnect from previous project if different
    if (this.projectId && this.projectId !== projectId) {
      await this.disconnect();
    }

    this.projectId = projectId;
    this.sessionId = sessionId || this.generateSessionId();
    this.callbacks = callbacks;
    this.isConnecting = true;

    try {
      // Create WebSocket service if needed
      if (!this.webSocketService) {
        this.webSocketService = createWebSocketService({
          enableAutoReconnect: true,
          maxReconnectAttempts: 3,
          reconnectInterval: 5000,
          heartbeatInterval: 30000,
          enableHeartbeat: true
        });

        this.setupHandlers();
      }

      // Connect to task updates endpoint
      const endpoint = `/api/projects/${projectId}/tasks/ws?session_id=${this.sessionId}`;
      await this.webSocketService.connect(endpoint);
      
      console.log(`🚀 Task Updates WebSocket connected for project: ${projectId}, session: ${this.sessionId}`);
    } catch (error) {
      console.error('Failed to connect task update WebSocket:', error);
      this.isConnecting = false;
      throw error;
    } finally {
      this.isConnecting = false;
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
      console.log(`📡 Task update WebSocket state changed: ${state}`);
      
      if (this.callbacks.onStateChange) {
        this.callbacks.onStateChange(state);
      }

      // Handle disconnection
      if (state === WebSocketState.DISCONNECTED || state === WebSocketState.FAILED) {
        if (this.callbacks.onClose) {
          this.callbacks.onClose();
        }
      }
    });

    // Handle errors
    this.webSocketService.addErrorHandler((error: Event | Error) => {
      console.error('Task update WebSocket error:', error);
      if (this.callbacks.onError) {
        this.callbacks.onError(error instanceof Error ? error : new Error('WebSocket error'));
      }
    });
  }

  private handleMessage(message: WebSocketMessage): void {
    const data = message as TaskUpdateData;
    console.log(`📨 Task update received for session ${this.sessionId}:`, data);

    switch (data.type) {
      case 'connection_established':
        console.log('🎯 Task updates connection established');
        if (this.callbacks.onConnectionEstablished) {
          this.callbacks.onConnectionEstablished();
        }
        break;
        
      case 'initial_tasks':
        console.log('📋 Initial tasks received:', data.data);
        if (this.callbacks.onInitialTasks) {
          this.callbacks.onInitialTasks(data.data.tasks || []);
        }
        break;
        
      case 'tasks_updated':
        console.log('🔄 Tasks updated via MCP:', data.data);
        if (this.callbacks.onTasksChange) {
          this.callbacks.onTasksChange(data.data.updated_tasks || []);
        }
        break;
        
      case 'task_created':
        console.log('🆕 Task created:', data.data);
        if (this.callbacks.onTaskCreated) {
          this.callbacks.onTaskCreated(data.data);
        }
        break;
        
      case 'task_updated':
        console.log('📝 Task updated:', data.data);
        if (this.callbacks.onTaskUpdated) {
          this.callbacks.onTaskUpdated(data.data);
        }
        break;
        
      case 'task_deleted':
        console.log('🗑️ Task deleted:', data.data);
        if (this.callbacks.onTaskDeleted) {
          this.callbacks.onTaskDeleted(data.data);
        }
        break;
        
      case 'task_archived':
        console.log('📦 Task archived:', data.data);
        if (this.callbacks.onTaskArchived) {
          this.callbacks.onTaskArchived(data.data);
        }
        break;
        
      case 'heartbeat':
        console.log('💓 Heartbeat received from server');
        // EnhancedWebSocketService handles heartbeat automatically
        break;
        
      case 'pong':
        console.log('🏓 Pong received from server');
        // Connection is alive
        break;
        
      default:
        console.warn('Unknown task update message type:', data.type);
    }
  }

  private generateSessionId(): string {
    return 'task-session-' + Math.random().toString(36).substr(2, 9);
  }

  sendPing(): void {
    if (this.webSocketService?.isConnected()) {
      this.webSocketService.send('ping');
    }
  }

  async disconnect(): Promise<void> {
    console.log(`🔌 Disconnecting Task Updates WebSocket`);
    
    if (this.webSocketService) {
      this.webSocketService.disconnect();
      this.webSocketService = null;
    }
    
    this.projectId = null;
    this.sessionId = null;
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
export const taskUpdateWebSocket = new TaskUpdateService();