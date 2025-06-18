import {
  EnhancedWebSocketService,
  createWebSocketService,
  WebSocketState,
  WebSocketMessage
} from './EnhancedWebSocketService';

/**
 * Enhanced WebSocket Service Wrapper
 * Provides backward compatibility while using the new EnhancedWebSocketService
 */
class WebSocketService {
  private enhancedService: EnhancedWebSocketService;
  
  constructor() {
    this.enhancedService = createWebSocketService({
      maxReconnectAttempts: 5,
      reconnectInterval: 1000,
      heartbeatInterval: 30000,
      enableAutoReconnect: true
    });
  }

  async connect(endpoint: string): Promise<void> {
    console.log(`Connecting to WebSocket endpoint: ${endpoint}`);
    await this.enhancedService.connect(endpoint);
  }
  
  addEventListener(type: string, listener: Function) {
    this.enhancedService.addMessageHandler(type, (message) => {
      listener(message);
    });
  }
  
  removeEventListener(type: string, listener: Function) {
    // Note: EnhancedWebSocketService doesn't support removing specific handlers by reference
    // This is a limitation of the migration
    console.warn('removeEventListener not fully supported in migration');
  }
  
  send(data: any) {
    this.enhancedService.send(data);
  }
  
  disconnect() {
    this.enhancedService.disconnect();
  }

  isConnected(): boolean {
    return this.enhancedService.isConnected();
  }
}

// Export singleton instances
export const knowledgeWebSocket = new WebSocketService();
export const crawlWebSocket = new WebSocketService();
export const projectListWebSocket = new WebSocketService();
export const healthWebSocket = new WebSocketService();

// Task Update WebSocket Service for real-time task updates
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
  onError?: (error: Event | Error) => void;
  onClose?: (event: CloseEvent) => void;
}

class TaskUpdateService {
  private enhancedService: EnhancedWebSocketService;
  private projectId: string | null = null;
  private sessionId: string | null = null;
  private callbacks: TaskUpdateCallbacks = {};

  constructor() {
    this.enhancedService = createWebSocketService({
      maxReconnectAttempts: 3,
      reconnectInterval: 5000,
      heartbeatInterval: 30000,
      enableAutoReconnect: true,
      enableHeartbeat: true
    });
  }

  async connect(projectId: string, callbacks: TaskUpdateCallbacks, sessionId?: string): Promise<void> {
    // Disconnect any existing connection
    if (this.isConnected()) {
      console.log('🔄 Closing existing WebSocket connection before creating new one');
      this.disconnect();
    }

    this.projectId = projectId;
    this.sessionId = sessionId || this.generateSessionId();
    this.callbacks = callbacks;
    
    // Include session ID as query parameter
    const endpoint = `/api/projects/${projectId}/tasks/ws?session_id=${this.sessionId}`;
    
    console.log(`🔌 Connecting to Task Updates WebSocket: ${endpoint}`);
    
    // Set up message handlers before connecting
    this.setupMessageHandlers();
    
    // Set up error handler
    if (callbacks.onError) {
      this.enhancedService.addErrorHandler(callbacks.onError);
    }
    
    // Set up state change handler for close events
    this.enhancedService.addStateChangeHandler((state) => {
      if (state === WebSocketState.DISCONNECTED && callbacks.onClose) {
        callbacks.onClose(new CloseEvent('close'));
      }
    });
    
    try {
      await this.enhancedService.connect(endpoint);
      console.log(`🔌 Task Updates WebSocket connected for project: ${projectId}, session: ${this.sessionId}`);
    } catch (error) {
      console.error('Failed to connect Task Updates WebSocket:', error);
      throw error;
    }
  }

  private generateSessionId(): string {
    return 'task-session-' + Math.random().toString(36).substr(2, 9);
  }

  private setupMessageHandlers(): void {
    // Handle all message types
    this.enhancedService.addMessageHandler('*', (message: WebSocketMessage) => {
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
          // Send ping response  
          this.sendPing();
          break;
          
        case 'pong':
          console.log('🏓 Pong received from server');
          // Connection is alive
          break;
          
        default:
          console.warn('Unknown task update message type:', data.type);
      }
    });
  }

  sendPing(): void {
    this.enhancedService.send('ping');
  }

  disconnect(): void {
    console.log(`🔌 Disconnecting Task Updates WebSocket`);
    this.enhancedService.disconnect();
    this.projectId = null;
    this.sessionId = null;
    this.callbacks = {};
  }

  isConnected(): boolean {
    return this.enhancedService.isConnected();
  }
}

// Export singleton instances
export const taskUpdateWebSocket = new TaskUpdateService(); 