/**
 * Agent Chat Service
 * Handles communication with AI agents via REST API and WebSocket streaming
 */

import {
  EnhancedWebSocketService,
  createWebSocketService,
  WebSocketState,
  WebSocketMessage,
  WebSocketConfig
} from './EnhancedWebSocketService';

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  agent_type?: string;
}

interface ChatSession {
  session_id: string;
  project_id?: string;
  messages: ChatMessage[];
  agent_type: string;
  created_at: Date;
}

interface ChatRequest {
  message: string;
  project_id?: string;
  context?: Record<string, any>;
}

class AgentChatService {
  private baseUrl: string;
  private wsConnections: Map<string, EnhancedWebSocketService> = new Map();
  private messageHandlers: Map<string, (message: ChatMessage) => void> = new Map();
  private typingHandlers: Map<string, (isTyping: boolean) => void> = new Map();
  private streamHandlers: Map<string, (chunk: string) => void> = new Map();
  private streamCompleteHandlers: Map<string, () => void> = new Map();
  private errorHandlers: Map<string, (error: Event | Error) => void> = new Map();
  private closeHandlers: Map<string, (event: CloseEvent) => void> = new Map();
  private reconnectTimeouts: Map<string, NodeJS.Timeout> = new Map();
  private reconnectAttempts: Map<string, number> = new Map();
  private readonly maxReconnectAttempts = 3; // Reduced from 5
  private readonly reconnectDelay = 1000; // 1 second initial delay
  
  // Add server status tracking
  private serverStatus: 'online' | 'offline' | 'unknown' | 'connecting' = 'unknown';
  private statusHandlers: Map<string, (status: 'online' | 'offline' | 'connecting') => void> = new Map();
  
  // Add session validation cache to prevent excessive validation requests
  private sessionValidationCache: Map<string, { valid: boolean; timestamp: number }> = new Map();
  private readonly sessionValidationTTL = 30000; // 30 seconds

  constructor() {
    // In development, the API is proxied through Vite, so we use the same origin
    // In production, this would be the actual API URL
    this.baseUrl = '';
  }

  /**
   * Get WebSocket URL for a session
   */
  private getWebSocketUrl(sessionId: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = '8080'; // Backend WebSocket port
    return `${protocol}//${host}:${port}/api/agent-chat/sessions/${sessionId}/ws`;
  }

  /**
   * Check if session validation is cached and still valid
   */
  private isSessionValidationCached(sessionId: string): boolean {
    const cached = this.sessionValidationCache.get(sessionId);
    if (!cached) return false;
    
    const now = Date.now();
    const isExpired = now - cached.timestamp > this.sessionValidationTTL;
    
    if (isExpired) {
      this.sessionValidationCache.delete(sessionId);
      return false;
    }
    
    return cached.valid;
  }

  /**
   * Cache session validation result
   */
  private cacheSessionValidation(sessionId: string, valid: boolean): void {
    this.sessionValidationCache.set(sessionId, {
      valid,
      timestamp: Date.now()
    });
  }

  /**
   * Clean up WebSocket connection and handlers for a session
   */
  private cleanupConnection(sessionId: string): void {
    // Clear any reconnect timeout
    const timeout = this.reconnectTimeouts.get(sessionId);
    if (timeout) {
      clearTimeout(timeout);
      this.reconnectTimeouts.delete(sessionId);
    }
    
    // Close WebSocket if open
    const ws = this.wsConnections.get(sessionId);
    if (ws) {
      ws.disconnect();
      this.wsConnections.delete(sessionId);
    }
    
    // Clear cached data only after session is recreated
    this.messageHandlers.delete(sessionId);
    this.typingHandlers.delete(sessionId);
    this.streamHandlers.delete(sessionId);
    this.streamCompleteHandlers.delete(sessionId);
    this.errorHandlers.delete(sessionId);
    this.closeHandlers.delete(sessionId);
    this.reconnectAttempts.delete(sessionId);
    
    // Clear session validation cache
    this.sessionValidationCache.delete(sessionId);
  }

  /**
   * Check if the chat server is online
   */
  private async checkServerStatus(): Promise<'online' | 'offline'> {
    try {
      const response = await fetch(`${this.baseUrl}/api/agent-chat/status`, {
        method: 'GET',
        timeout: 5000, // 5 second timeout
      } as RequestInit);
      
      if (response.ok) {
        this.serverStatus = 'online';
        return 'online';
      } else {
        this.serverStatus = 'offline';
        return 'offline';
      }
    } catch (error) {
      console.log('Server status check failed:', error);
      this.serverStatus = 'offline';
      return 'offline';
    }
  }

  /**
   * Notify status change to all sessions
   */
  private notifyStatusChange(status: 'online' | 'offline' | 'connecting', sessionId?: string): void {
    this.serverStatus = status;
    
    if (sessionId) {
      // Notify specific session
      const handler = this.statusHandlers.get(sessionId);
      if (handler) {
        console.log(`📡 Notifying session ${sessionId} of status change: ${status}`);
        handler(status);
      }
    } else {
      // Notify all sessions
      console.log(`📡 Notifying all sessions of status change: ${status}`);
      this.statusHandlers.forEach((handler, sid) => {
        console.log(`📡 Notifying session ${sid} of status: ${status}`);
        handler(status);
      });
    }
  }

  /**
   * Schedule a reconnection attempt with server status checking
   */
  private async scheduleReconnect(sessionId: string): Promise<void> {
    const attempts = this.reconnectAttempts.get(sessionId) || 0;
    
    if (attempts >= this.maxReconnectAttempts) {
      console.log(`Max reconnection attempts (${this.maxReconnectAttempts}) reached for session ${sessionId}`);
      this.notifyStatusChange('offline', sessionId);
      // Clean up completely after max attempts
      this.cleanupConnection(sessionId);
      return;
    }
    
    // Clear any existing reconnection timeout first
    const existingTimeout = this.reconnectTimeouts.get(sessionId);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
      this.reconnectTimeouts.delete(sessionId);
    }
    
    // Exponential backoff: delay = baseDelay * (2^attempts) with max of 30 seconds
    const delay = Math.min(this.reconnectDelay * Math.pow(2, attempts), 30000);
    console.log(`⏰ Scheduling reconnection attempt ${attempts + 1}/${this.maxReconnectAttempts} for session ${sessionId} in ${delay}ms`);
    
    this.notifyStatusChange('connecting', sessionId);
    
    const timeoutId = setTimeout(() => {
      if (this.reconnectTimeouts.has(sessionId)) {
        this.reconnectTimeouts.delete(sessionId);
        
        // Check if we still have handlers before attempting reconnection
        const messageHandler = this.messageHandlers.get(sessionId);
        const typingHandler = this.typingHandlers.get(sessionId);
        
        if (messageHandler && typingHandler) {
          console.log(`🔄 Attempting reconnection ${attempts + 1}/${this.maxReconnectAttempts} for session ${sessionId}`);
          this.connectWebSocket(
            sessionId,
            messageHandler,
            typingHandler,
            this.streamHandlers.get(sessionId),
            this.streamCompleteHandlers.get(sessionId),
            this.errorHandlers.get(sessionId),
            this.closeHandlers.get(sessionId)
          );
        } else {
          console.log(`No handlers found for session ${sessionId}, skipping reconnection`);
          this.cleanupConnection(sessionId);
        }
      }
    }, delay);

    this.reconnectAttempts.set(sessionId, attempts + 1);
    this.reconnectTimeouts.set(sessionId, timeoutId);
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleIncomingMessage(
    wsMessage: WebSocketMessage,
    onMessage: (message: ChatMessage) => void,
    onTyping: (isTyping: boolean) => void,
    onStreamChunk?: (chunk: string) => void,
    onStreamComplete?: () => void
  ): void {
    try {
      console.log(`Processing WebSocket message:`, wsMessage);
      
      switch (wsMessage.type) {
        case 'message':
          if (wsMessage.data) {
            const chatMessage: ChatMessage = {
              id: wsMessage.data.id || new Date().toISOString(),
              content: wsMessage.data.content || wsMessage.content || '',
              sender: wsMessage.data.sender || 'agent',
              timestamp: wsMessage.data.timestamp ? new Date(wsMessage.data.timestamp) : new Date(),
              agent_type: wsMessage.data.agent_type,
            };
            onMessage(chatMessage);
          }
          break;
          
        case 'typing':
          onTyping(wsMessage.is_typing || false);
          break;
          
        case 'stream_chunk':
          if (onStreamChunk && wsMessage.content) {
            onStreamChunk(wsMessage.content);
          }
          break;
          
        case 'stream_complete':
          if (onStreamComplete) {
            onStreamComplete();
          }
          break;
          
        case 'connection_confirmed':
          console.log('🟢 Connection confirmed by server');
          break;
          
        case 'heartbeat':
          // Server heartbeat - respond with ping
          console.log('💓 Received heartbeat from server');
          // EnhancedWebSocketService handles heartbeat automatically
          break;
          
        case 'pong':
          // Response to our ping - connection is alive
          console.log('🏓 Received pong from server');
          break;
          
        default:
          console.warn('Unknown WebSocket message type:', wsMessage.type);
      }
    } catch (error) {
      console.error('Error processing WebSocket message:', error);
    }
  }

  /**
   * Create a new chat session with an agent
   */
  async createSession(projectId?: string, agentType: string = 'docs'): Promise<{ session_id: string }> {
    const requestBody = {
      project_id: projectId,
      agent_type: agentType,
    };
    console.log(`[AGENT SERVICE] Creating session with body:`, requestBody);
    const url = `${this.baseUrl}/api/agent-chat/sessions`;
    console.log(`[AGENT SERVICE] POST to URL:`, url);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      throw new Error(`Failed to create chat session: ${response.statusText}`);
    }

    const data = await response.json();
    return { session_id: data.session_id || data.id };
  }

  /**
   * Get chat session details
   */
  async getSession(sessionId: string): Promise<ChatSession> {
    const response = await fetch(`${this.baseUrl}/api/agent-chat/sessions/${sessionId}`);

    if (!response.ok) {
      throw new Error(`Failed to get chat session: ${response.statusText}`);
    }

    const data = await response.json();
    
    // Handle different response formats
    const session = data.session || data;
    
    // Convert timestamps to Date objects
    if (typeof session.created_at === 'string') {
      session.created_at = new Date(session.created_at);
    }
    
    if (session.messages) {
      session.messages = session.messages.map((msg: any) => ({
        ...msg,
        timestamp: typeof msg.timestamp === 'string' ? new Date(msg.timestamp) : msg.timestamp
      }));
    }

    return session;
  }

  /**
   * Send a message in a chat session
   */
  async sendMessage(
    sessionId: string,
    message: string,
    context?: Record<string, any>
  ): Promise<void> {
    const chatRequest: ChatRequest = {
      message,
      context,
    };

    const response = await fetch(
      `${this.baseUrl}/api/agent-chat/sessions/${sessionId}/messages`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(chatRequest),
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to send message: ${response.statusText}`);
    }
  }

  /**
   * Connect to WebSocket for real-time communication
   */
  async connectWebSocket(
    sessionId: string,
    onMessage: (message: ChatMessage) => void,
    onTyping: (isTyping: boolean) => void,
    onStreamChunk?: (chunk: string) => void,
    onStreamComplete?: () => void,
    onError?: (error: Event | Error) => void,
    onClose?: (event: CloseEvent) => void
  ): Promise<void> {
    // Check and close any existing connection properly
    const existingWs = this.wsConnections.get(sessionId);
    if (existingWs) {
      console.log(`🧹 Cleaning up existing WebSocket for session ${sessionId}`);
      existingWs.disconnect();
      this.wsConnections.delete(sessionId);
    }

    // Store handlers for reconnection
    this.messageHandlers.set(sessionId, onMessage);
    this.typingHandlers.set(sessionId, onTyping);
    
    if (onStreamChunk) {
      this.streamHandlers.set(sessionId, onStreamChunk);
    }
    
    if (onStreamComplete) {
      this.streamCompleteHandlers.set(sessionId, onStreamComplete);
    }
    
    if (onError) {
      this.errorHandlers.set(sessionId, onError);
    }
    
    if (onClose) {
      this.closeHandlers.set(sessionId, onClose);
    }

    // Reset reconnect attempts
    this.reconnectAttempts.set(sessionId, 0);

    // Create WebSocket connection
    const wsService = createWebSocketService(this.getWebSocketConfig());
    this.wsConnections.set(sessionId, wsService);
    
    // Set up message handler
    wsService.addMessageHandler('*', (message) => {
      this.handleIncomingMessage(
        message,
        onMessage,
        onTyping,
        onStreamChunk,
        onStreamComplete
      );
    });
    
    // Set up error handler
    if (onError) {
      wsService.addErrorHandler(onError);
    }
    
    // Set up state change handler
    wsService.addStateChangeHandler((state) => {
      switch (state) {
        case WebSocketState.CONNECTED:
          console.log(`🟢 WebSocket connected for session ${sessionId}`);
          this.reconnectAttempts.set(sessionId, 0);
          this.notifyStatusChange('online', sessionId);
          break;
          
        case WebSocketState.DISCONNECTED:
          console.log(`🔌 WebSocket disconnected for session ${sessionId}`);
          this.notifyStatusChange('offline', sessionId);
          
          // Handle session invalidation or schedule reconnect
          if (onClose) {
            onClose(new CloseEvent('close'));
          }
          break;
          
        case WebSocketState.RECONNECTING:
          console.log(`🟢 WebSocket reconnecting for session ${sessionId}`);
          this.notifyStatusChange('connecting', sessionId);
          break;
          
        case WebSocketState.FAILED:
          console.log(`❌ WebSocket failed for session ${sessionId}`);
          this.notifyStatusChange('offline', sessionId);
          this.handleSessionInvalidation(sessionId);
          break;
      }
    });
    
    try {
      const endpoint = `/api/agent-chat/sessions/${sessionId}/ws`;
      console.log(`🔌 Attempting to connect WebSocket to: ${endpoint}`);
      await wsService.connect(endpoint);
    } catch (error) {
      console.error(`❌ Failed to connect WebSocket for session ${sessionId}:`, error);
      throw error;
    }
  }

  /**
   * Disconnect WebSocket for a session
   */
  disconnectWebSocket(sessionId: string): void {
    this.cleanupConnection(sessionId);
  }

  /**
   * Disconnect all WebSocket connections
   */
  disconnectAll(): void {
    this.wsConnections.forEach((_, sessionId) => {
      this.disconnectWebSocket(sessionId);
    });
  }

  /**
   * Check if WebSocket is connected for a session
   */
  isConnected(sessionId: string): boolean {
    const ws = this.wsConnections.get(sessionId);
    return ws?.isConnected() ?? false;
  }

  /**
   * Get WebSocket connection state for a session
   */
  getConnectionState(sessionId: string): WebSocketState | null {
    const ws = this.wsConnections.get(sessionId);
    return ws?.state ?? null;
  }

  /**
   * Handle session invalidation by creating a new session
   */
  private async handleSessionInvalidation(oldSessionId: string): Promise<void> {
    console.log(`🔄 Handling session invalidation for ${oldSessionId}`);
    
    try {
      // Try to verify if the session really doesn't exist
      const response = await fetch(`${this.baseUrl}/api/agent-chat/sessions/${oldSessionId}`);
      
      if (response.status === 403 || response.status === 404) {
        console.log(`✅ Confirmed session ${oldSessionId} is invalid, creating new session`);
        
        // Clean up the old session data
        this.cleanupConnection(oldSessionId);
        
        // Create a new session (assuming same agent type)
        const newSession = await this.createSession(undefined, 'docs');
        console.log(`🆕 Created new session: ${newSession.session_id}`);
        
        // Transfer handlers to new session
        const messageHandler = this.messageHandlers.get(oldSessionId);
        const typingHandler = this.typingHandlers.get(oldSessionId);
        const streamHandler = this.streamHandlers.get(oldSessionId);
        const streamCompleteHandler = this.streamCompleteHandlers.get(oldSessionId);
        const errorHandler = this.errorHandlers.get(oldSessionId);
        const closeHandler = this.closeHandlers.get(oldSessionId);
        
        // Clean up old handlers
        this.messageHandlers.delete(oldSessionId);
        this.typingHandlers.delete(oldSessionId);
        this.streamHandlers.delete(oldSessionId);
        this.streamCompleteHandlers.delete(oldSessionId);
        this.errorHandlers.delete(oldSessionId);
        this.closeHandlers.delete(oldSessionId);
        
        // Connect with new session if handlers exist
        if (messageHandler && typingHandler) {
          console.log(`🔌 Reconnecting with new session ${newSession.session_id}`);
          this.connectWebSocket(
            newSession.session_id,
            messageHandler,
            typingHandler,
            streamHandler,
            streamCompleteHandler,
            errorHandler,
            closeHandler
          );
          
          // Notify about session change via error handler (since we don't have a dedicated callback)
          if (errorHandler) {
            const sessionChangeEvent = new Event('sessionchange') as any;
            sessionChangeEvent.oldSessionId = oldSessionId;
            sessionChangeEvent.newSessionId = newSession.session_id;
            errorHandler(sessionChangeEvent);
          }
        }
      } else {
        // Session exists, might just be a temporary connection issue
        console.log(`Session ${oldSessionId} still exists, scheduling normal reconnect`);
        this.scheduleReconnect(oldSessionId);
      }
    } catch (error) {
      console.error(`Error handling session invalidation for ${oldSessionId}:`, error);
      // Fallback to normal reconnection
      this.scheduleReconnect(oldSessionId);
    }
  }

  /**
   * Get current active session ID (useful after session recovery)
   */
  getCurrentSessionId(): string | null {
    // Return the first active session ID, or null if none
    for (const [sessionId, ws] of this.wsConnections.entries()) {
      if (ws.isConnected()) {
        return sessionId;
      }
    }
    return null;
  }

  /**
   * Get all active session IDs
   */
  getActiveSessions(): string[] {
    return Array.from(this.wsConnections.keys()).filter(sessionId => {
      const ws = this.wsConnections.get(sessionId);
      return ws && ws.isConnected();
    });
  }

  /**
   * Manually attempt to reconnect (for user-triggered reconnection)
   */
  async manualReconnect(sessionId: string): Promise<boolean> {
    console.log(`🔄 Manual reconnection attempt for session ${sessionId}`);
    
    // First check if server is back online
    this.notifyStatusChange('connecting');
    const serverStatus = await this.checkServerStatus();
    
    if (serverStatus === 'offline') {
      console.log('Server is still offline');
      this.notifyStatusChange('offline');
      return false;
    }
    
    // Clean up any existing connection
    this.cleanupConnection(sessionId);
    
    // Reset reconnect attempts for fresh start
    this.reconnectAttempts.delete(sessionId);
    
    try {
      // Try to verify/create session first
      let validSessionId = sessionId;
      
      try {
        // Check if session still exists
        await this.getSession(sessionId);
      } catch (error) {
        // Session doesn't exist, create a new one
        console.log('Session no longer exists, creating new session');
        const newSession = await this.createSession(undefined, 'docs');
        validSessionId = newSession.session_id;
      }
      
      // Reconnect with valid session
      const messageHandler = this.messageHandlers.get(sessionId);
      const typingHandler = this.typingHandlers.get(sessionId);
      
      if (messageHandler && typingHandler) {
        this.connectWebSocket(
          validSessionId,
          messageHandler,
          typingHandler,
          this.streamHandlers.get(sessionId),
          this.streamCompleteHandlers.get(sessionId),
          this.errorHandlers.get(sessionId),
          this.closeHandlers.get(sessionId)
        );
        
        this.notifyStatusChange('online');
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Manual reconnection failed:', error);
      this.notifyStatusChange('offline');
      return false;
    }
  }

  /**
   * Subscribe to connection status changes
   */
  onStatusChange(sessionId: string, handler: (status: 'online' | 'offline' | 'connecting') => void): void {
    this.statusHandlers.set(sessionId, handler);
  }

  /**
   * Unsubscribe from status changes
   */
  offStatusChange(sessionId: string): void {
    this.statusHandlers.delete(sessionId);
  }

  /**
   * Get current server status
   */
  getServerStatus(): 'online' | 'offline' | 'unknown' | 'connecting' {
    return this.serverStatus;
  }

  private getWebSocketConfig(): WebSocketConfig {
    return {
      maxReconnectAttempts: this.maxReconnectAttempts,
      reconnectInterval: this.reconnectDelay,
      heartbeatInterval: 30000,
      enableAutoReconnect: true,
      enableHeartbeat: true,
    };
  }
}

// Export singleton instance
export const agentChatService = new AgentChatService();
export type { ChatMessage, ChatSession, ChatRequest };
