import type { Project } from '../types/project';
import {
  EnhancedWebSocketService,
  WebSocketState,
  WebSocketMessage,
  createWebSocketService
} from './EnhancedWebSocketService';

export interface ProjectCreationProgressData {
  progressId: string;
  status: 'starting' | 'initializing_agents' | 'generating_docs' | 'processing_requirements' | 'ai_generation' | 'finalizing_docs' | 'saving_to_database' | 'completed' | 'error';
  percentage: number;
  step?: string;
  currentStep?: string;
  eta?: string;
  error?: string;
  logs: string[];
  project?: Project; // The created project when completed
  duration?: string;
}

interface StreamProgressOptions {
  autoReconnect?: boolean;
  reconnectDelay?: number;
}

type ProgressCallback = (data: ProjectCreationProgressData) => void;

class ProjectCreationProgressService {
  private baseUrl: string;
  private webSocketService: EnhancedWebSocketService | null = null;
  private currentProgressId: string | null = null;

  constructor() {
    this.baseUrl = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8080';
  }

  /**
   * Stream project creation progress using EnhancedWebSocketService
   */
  async streamProgress(
    progressId: string,
    onMessage: ProgressCallback,
    options: StreamProgressOptions = {}
  ): Promise<void> {
    const { autoReconnect = true, reconnectDelay = 5000 } = options;

    // Disconnect from previous progress if any
    if (this.currentProgressId && this.currentProgressId !== progressId) {
      await this.disconnect();
    }

    this.currentProgressId = progressId;

    try {
      // Create WebSocket service if needed
      if (!this.webSocketService) {
        this.webSocketService = createWebSocketService({
          enableAutoReconnect: autoReconnect,
          reconnectInterval: reconnectDelay,
          maxReconnectAttempts: 5,
          heartbeatInterval: 30000,
          enableHeartbeat: true
        });

        this.setupHandlers(onMessage);
      }

      // Connect to the progress endpoint
      const endpoint = `/api/project-creation-progress/${progressId}`;
      await this.webSocketService.connect(endpoint);
      
      console.log(`🚀 Connected to project creation progress stream: ${progressId}`);
    } catch (error) {
      console.error(`Failed to connect to project creation progress stream: ${progressId}`, error);
      this.currentProgressId = null;
      throw error;
    }
  }

  private setupHandlers(onMessage: ProgressCallback): void {
    if (!this.webSocketService) return;

    // Handle different message types
    this.webSocketService.addMessageHandler('*', (message: WebSocketMessage) => {
      // Ignore ping messages
      if (message.type === 'ping' || message.type === 'pong' || message.type === 'heartbeat') {
        return;
      }

      // Handle progress messages
      if (message.type === 'project_progress' || message.type === 'project_completed' || message.type === 'project_error') {
        if (message.data) {
          onMessage(message.data);
        }
      }
    });

    // Handle connection state changes
    this.webSocketService.addStateChangeHandler((state: WebSocketState) => {
      console.log(`📡 Project creation progress WebSocket state changed: ${state}`);
    });

    // Handle errors
    this.webSocketService.addErrorHandler((error: Event | Error) => {
      console.error('Project creation progress WebSocket error:', error);
    });
  }

  /**
   * Disconnect from progress stream
   */
  async disconnect(): Promise<void> {
    if (this.webSocketService) {
      this.webSocketService.disconnect();
      this.webSocketService = null;
    }
    
    this.currentProgressId = null;
    console.log('🔌 Disconnected from project creation progress stream');
  }

  /**
   * Check if currently connected to a progress stream
   */
  isConnected(): boolean {
    return this.webSocketService?.isConnected() || false;
  }

  /**
   * Get current connection state
   */
  getConnectionState(): WebSocketState {
    return this.webSocketService?.state || WebSocketState.DISCONNECTED;
  }
}

// Export singleton instance
export const projectCreationProgressService = new ProjectCreationProgressService(); 