/**
 * Agent Chat Service
 * Handles communication with AI agents via REST API and WebSocket streaming
 */

interface ChatMessage {
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

interface WebSocketMessage {
  type: 'message' | 'typing' | 'ping' | 'stream_chunk' | 'stream_complete' | 'connection_confirmed' | 'heartbeat' | 'pong';
  data?: any;
  content?: string;
  session_id?: string;
  is_typing?: boolean;
}

class AgentChatService {
  private baseUrl: string;
  private wsConnections: Map<string, WebSocket> = new Map();
  private messageHandlers: Map<string, (message: ChatMessage) => void> = new Map();
  private typingHandlers: Map<string, (isTyping: boolean) => void> = new Map();
  private streamHandlers: Map<string, (chunk: string) => void> = new Map();
  private streamCompleteHandlers: Map<string, () => void> = new Map();
  private errorHandlers: Map<string, (error: Event) => void> = new Map();
  private closeHandlers: Map<string, (event: CloseEvent) => void> = new Map();
  private reconnectTimeouts: Map<string, NodeJS.Timeout> = new Map();
  private reconnectAttempts: Map<string, number> = new Map();
  private readonly maxReconnectAttempts = 3; // Reduced from 5
  private readonly reconnectDelay = 1000; // 1 second initial delay
  
  // Add server status tracking
  private serverStatus: 'online' | 'offline' | 'unknown' = 'unknown';
  private statusHandlers: Map<string, (status: 'online' | 'offline' | 'connecting') => void> = new Map();

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080';
  }

  /**
   * Get WebSocket URL for a session
   */
  private getWebSocketUrl(sessionId: string): string {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = new URL(this.baseUrl).host;
    return `${wsProtocol}//${host}/api/agent-chat/sessions/${sessionId}/ws`;
  }

  /**
   * Clean up WebSocket connection and handlers for a session
   */
  private cleanupConnection(sessionId: string): void {
    // Clear any pending reconnection attempt
    const reconnectTimeout = this.reconnectTimeouts.get(sessionId);
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      this.reconnectTimeouts.delete(sessionId);
    }
    
    // Close WebSocket if it exists
    const ws = this.wsConnections.get(sessionId);
    if (ws) {
      // Be more careful about closing connections
      if (ws.readyState === WebSocket.OPEN) {
        console.log(`Closing WebSocket connection for session ${sessionId}`);
        ws.close(1000, 'Client disconnected');
      } else if (ws.readyState === WebSocket.CONNECTING) {
        console.log(`Aborting connecting WebSocket for session ${sessionId}`);
        // For connecting sockets, we need to wait or force close
        ws.close();
      }
      this.wsConnections.delete(sessionId);
    }
    
    // Remove all handlers
    this.messageHandlers.delete(sessionId);
    this.typingHandlers.delete(sessionId);
    this.streamHandlers.delete(sessionId);
    this.streamCompleteHandlers.delete(sessionId);
    this.errorHandlers.delete(sessionId);
    this.closeHandlers.delete(sessionId);
    this.reconnectAttempts.delete(sessionId);
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
  private notifyStatusChange(status: 'online' | 'offline' | 'connecting'): void {
    this.statusHandlers.forEach(handler => {
      try {
        handler(status);
      } catch (error) {
        console.error('Error in status handler:', error);
      }
    });
  }

  /**
   * Schedule a reconnection attempt with server status checking
   */
  private async scheduleReconnect(sessionId: string): Promise<void> {
    const attempts = this.reconnectAttempts.get(sessionId) || 0;
    
    if (attempts >= this.maxReconnectAttempts) {
      console.log(`Max reconnection attempts (${this.maxReconnectAttempts}) reached for session ${sessionId}`);
      
      // Check server status before giving up
      const serverStatus = await this.checkServerStatus();
      if (serverStatus === 'offline') {
        console.log('Server appears to be offline, stopping automatic reconnection');
        this.notifyStatusChange('offline');
        this.cleanupConnection(sessionId);
        return;
      }
      
      console.error(`Server is online but session ${sessionId} cannot connect after ${this.maxReconnectAttempts} attempts`);
      this.cleanupConnection(sessionId);
      return;
    }

    // Check server status before attempting reconnection
    this.notifyStatusChange('connecting');
    const serverStatus = await this.checkServerStatus();
    
    if (serverStatus === 'offline') {
      console.log('Server is offline, stopping automatic reconnection');
      this.notifyStatusChange('offline');
      this.cleanupConnection(sessionId);
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, attempts);
    console.log(`Server is online, attempting to reconnect in ${delay}ms (attempt ${attempts + 1}/${this.maxReconnectAttempts})`);
    
    const timeoutId = setTimeout(() => {
      if (this.reconnectTimeouts.has(sessionId)) {
        this.reconnectTimeouts.delete(sessionId);
        this.connectWebSocket(
          sessionId,
          this.messageHandlers.get(sessionId)!,
          this.typingHandlers.get(sessionId)!,
          this.streamHandlers.get(sessionId),
          this.streamCompleteHandlers.get(sessionId),
          this.errorHandlers.get(sessionId),
          this.closeHandlers.get(sessionId)
        );
      }
    }, delay);

    this.reconnectAttempts.set(sessionId, attempts + 1);
    this.reconnectTimeouts.set(sessionId, timeoutId);
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleIncomingMessage(
    event: MessageEvent,
    onMessage: (message: ChatMessage) => void,
    onTyping: (isTyping: boolean) => void,
    onStreamChunk?: (chunk: string) => void,
    onStreamComplete?: () => void
  ): void {
    try {
      const wsMessage = JSON.parse(event.data) as WebSocketMessage;
      
      switch (wsMessage.type) {
        case 'message':
          if (wsMessage.data) {
            // Ensure timestamp is a Date object
            if (typeof wsMessage.data.timestamp === 'string') {
              wsMessage.data.timestamp = new Date(wsMessage.data.timestamp);
            }
            onMessage(wsMessage.data);
          }
          break;
          
        case 'typing':
          // Handle both possible formats for typing status
          const isTyping = wsMessage.is_typing === true || 
                         (wsMessage.data && wsMessage.data.is_typing === true);
          onTyping(isTyping);
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
          
        case 'ping':
          // Keep connection alive - no action needed
          break;
          
        case 'connection_confirmed':
          // Connection established successfully
          console.log('✅ Agent chat WebSocket connection confirmed');
          break;
          
        case 'heartbeat':
          // Server heartbeat - respond with ping
          console.log('💓 Received heartbeat from server');
          // Find the sessionId from the connection map
          const currentSessionId = wsMessage.session_id || Array.from(this.wsConnections.entries()).find(([_, ws]) => ws === event.target)?.[0];
          if (currentSessionId && this.wsConnections.get(currentSessionId)) {
            this.wsConnections.get(currentSessionId)?.send('ping');
          }
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
    const response = await fetch(`${this.baseUrl}/api/agent-chat/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        project_id: projectId,
        agent_type: agentType,
      }),
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
  connectWebSocket(
    sessionId: string,
    onMessage: (message: ChatMessage) => void,
    onTyping: (isTyping: boolean) => void,
    onStreamChunk?: (chunk: string) => void,
    onStreamComplete?: () => void,
    onError?: (error: Event) => void,
    onClose?: (event: CloseEvent) => void
  ): void {
    // Check and close any existing connection properly
    const existingWs = this.wsConnections.get(sessionId);
    if (existingWs) {
      console.log(`🧹 Cleaning up existing WebSocket for session ${sessionId}, state: ${existingWs.readyState}`);
      // Always close existing connection regardless of state
      if (existingWs.readyState === WebSocket.OPEN || existingWs.readyState === WebSocket.CONNECTING) {
        existingWs.close(1000, 'Reconnecting');
      }
      this.wsConnections.delete(sessionId);
      
             // If it was still connecting, we'll just proceed - the close() call above will handle it
       if (existingWs.readyState === WebSocket.CONNECTING) {
         console.log(`⚠️ Previous connection was still connecting, forced close initiated`);
       }
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
    const wsUrl = this.getWebSocketUrl(sessionId);
    console.log(`🔌 Attempting to connect WebSocket to: ${wsUrl}`);
    
    const ws = new WebSocket(wsUrl);
    this.wsConnections.set(sessionId, ws);

    ws.onopen = () => {
      console.log(`🚀 WebSocket connected for session ${sessionId}`);
      // Reset reconnect attempts on successful connection
      this.reconnectAttempts.set(sessionId, 0);
    };

    ws.onmessage = (event) => {
      console.log(`📨 WebSocket message received for session ${sessionId}:`, event.data);
      this.handleIncomingMessage(
        event,
        onMessage,
        onTyping,
        onStreamChunk,
        onStreamComplete
      );
    };

    ws.onerror = (error) => {
      console.error(`❌ WebSocket error for session ${sessionId}:`, error);
      console.error(`WebSocket state at error: ${ws.readyState} (0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED)`);
      
      // Check if this might be a 403 Forbidden error by attempting to verify the session
      if (ws.readyState === WebSocket.CLOSED) {
        console.log(`🔍 WebSocket closed immediately, checking if session ${sessionId} is valid`);
        // Use setTimeout to avoid blocking the error handler
        setTimeout(async () => {
          try {
            const response = await fetch(`${this.baseUrl}/api/agent-chat/sessions/${sessionId}`);
            if (response.status === 403 || response.status === 404) {
              console.log(`🚨 Session ${sessionId} is invalid (${response.status}), triggering session recovery`);
              await this.handleSessionInvalidation(sessionId);
              return; // Don't call onError since we're handling it
            }
          } catch (fetchError) {
            console.log(`Could not verify session ${sessionId}:`, fetchError);
          }
          
          // If session verification fails or session is valid, call the original error handler
          if (onError) {
            onError(error);
          }
        }, 100);
      } else {
        // Normal error handling for other cases
        if (onError) {
          onError(error);
        }
      }
    };

    ws.onclose = (event) => {
      console.log(`🔌 WebSocket closed for session ${sessionId}:`, event.code, event.reason);
      console.log(`Close event details: wasClean=${event.wasClean}, code=${event.code}, reason="${event.reason}"`);
      this.wsConnections.delete(sessionId);
      
      // Handle different close codes
      if (event.code === 4004) {
        // 4004 = Custom code from backend indicating "Session not found"
        console.warn(`🚨 Backend says session ${sessionId} not found (code 4004), triggering session recovery`);
        this.handleSessionInvalidation(sessionId);
      } else if (event.code === 1006) {
        // 1006 = abnormal closure, often indicates connection issues
        console.log(`Connection lost unexpectedly (code 1006) for session ${sessionId}`);
        this.scheduleReconnect(sessionId);
      } else if (event.code === 1002 || event.code === 1003) {
        // 1002/1003 = protocol errors, likely session invalidation
        console.warn(`Session ${sessionId} may be invalid, attempting session recovery`);
        this.handleSessionInvalidation(sessionId);
      } else if (event.code !== 1000) { 
        // 1000 is normal closure, anything else might need reconnection
        console.log(`Scheduling reconnect for abnormal closure (code ${event.code})`);
        this.scheduleReconnect(sessionId);
      }
      
      if (onClose) {
        onClose(event);
      }
    };
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
    return ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get WebSocket connection state for a session
   */
  getConnectionState(sessionId: string): number | null {
    const ws = this.wsConnections.get(sessionId);
    return ws?.readyState ?? null;
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
   * Get the current active session ID (useful after session recovery)
   */
  getCurrentSessionId(): string | null {
    // Return the first active session ID, or null if none
    for (const [sessionId, ws] of this.wsConnections.entries()) {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
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
      return ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING);
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
  getServerStatus(): 'online' | 'offline' | 'unknown' {
    return this.serverStatus;
  }
}

// Export singleton instance
export const agentChatService = new AgentChatService();
export type { ChatMessage, ChatSession, ChatRequest };
