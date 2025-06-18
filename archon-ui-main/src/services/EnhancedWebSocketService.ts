/**
 * Enhanced WebSocket Service
 * 
 * Features:
 * - Connection state management
 * - Promise-based connection establishment
 * - Exponential backoff for reconnections
 * - Typed message handlers
 * - Support for dynamic endpoints
 * - Heartbeat/keepalive support
 * - Better error handling and recovery
 */

export enum WebSocketState {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  RECONNECTING = 'RECONNECTING',
  DISCONNECTED = 'DISCONNECTED',
  FAILED = 'FAILED'
}

export interface WebSocketConfig {
  maxReconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
  messageTimeout?: number;
  enableHeartbeat?: boolean;
  enableAutoReconnect?: boolean;
}

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
  [key: string]: any;
}

type MessageHandler = (message: WebSocketMessage) => void;
type ErrorHandler = (error: Event | Error) => void;
type StateChangeHandler = (state: WebSocketState) => void;

export class EnhancedWebSocketService {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketConfig>;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private messageTimeout: NodeJS.Timeout | null = null;
  private lastMessageTime = 0;
  
  private messageHandlers: Map<string, MessageHandler[]> = new Map();
  private errorHandlers: ErrorHandler[] = [];
  private stateChangeHandlers: StateChangeHandler[] = [];
  private connectionPromise: Promise<void> | null = null;
  private connectionResolver: (() => void) | null = null;
  private connectionRejector: ((error: Error) => void) | null = null;
  
  private _state: WebSocketState = WebSocketState.DISCONNECTED;
  private endpoint: string = '';

  constructor(config: WebSocketConfig = {}) {
    this.config = {
      maxReconnectAttempts: 5,
      reconnectInterval: 1000,
      heartbeatInterval: 30000,
      messageTimeout: 60000,
      enableHeartbeat: true,
      enableAutoReconnect: true,
      ...config
    };
  }

  get state(): WebSocketState {
    return this._state;
  }

  private setState(newState: WebSocketState): void {
    if (this._state !== newState) {
      this._state = newState;
      this.notifyStateChange(newState);
    }
  }

  /**
   * Connect to WebSocket with promise-based connection establishment
   */
  async connect(endpoint: string): Promise<void> {
    // If already connected to the same endpoint, return existing connection
    if (this.ws && this.state === WebSocketState.CONNECTED && this.endpoint === endpoint) {
      return Promise.resolve();
    }

    // If currently connecting, return existing promise
    if (this.connectionPromise && this.state === WebSocketState.CONNECTING) {
      return this.connectionPromise;
    }

    // Disconnect from current endpoint if different
    if (this.endpoint && this.endpoint !== endpoint) {
      this.disconnect();
    }

    this.endpoint = endpoint;
    this.setState(WebSocketState.CONNECTING);

    // Create connection promise
    this.connectionPromise = new Promise<void>((resolve, reject) => {
      this.connectionResolver = resolve;
      this.connectionRejector = reject;
    });

    try {
      await this.establishConnection();
      return this.connectionPromise;
    } catch (error) {
      this.setState(WebSocketState.FAILED);
      throw error;
    }
  }

  private async establishConnection(): Promise<void> {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = '8080'; // Backend WebSocket port
    const wsUrl = `${protocol}//${host}:${port}${this.endpoint}`;
    
    console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);
    
    try {
      this.ws = new WebSocket(wsUrl);
      this.setupEventHandlers();
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.handleConnectionError(error as Error);
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log(`✅ WebSocket connected to ${this.endpoint}`);
      this.setState(WebSocketState.CONNECTED);
      this.reconnectAttempts = 0;
      this.lastMessageTime = Date.now();
      
      // Start heartbeat if enabled
      if (this.config.enableHeartbeat) {
        this.startHeartbeat();
      }
      
      // Start message timeout monitoring
      this.startMessageTimeoutMonitoring();
      
      // Resolve connection promise
      if (this.connectionResolver) {
        this.connectionResolver();
        this.connectionResolver = null;
        this.connectionRejector = null;
      }
    };

    this.ws.onmessage = (event) => {
      this.lastMessageTime = Date.now();
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
        console.error('Raw message:', event.data);
      }
    };

    this.ws.onclose = (event) => {
      console.log(`🔌 WebSocket disconnected from ${this.endpoint}`, {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      
      this.cleanup();
      
      // Handle reconnection based on close code
      if (this.shouldReconnect(event)) {
        this.setState(WebSocketState.RECONNECTING);
        this.attemptReconnect();
      } else {
        this.setState(WebSocketState.DISCONNECTED);
      }
      
      // Reject connection promise if still pending
      if (this.connectionRejector) {
        this.connectionRejector(new Error(`WebSocket closed: ${event.reason || 'Unknown reason'}`));
        this.connectionResolver = null;
        this.connectionRejector = null;
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.notifyError(error);
      
      // Reject connection promise if still pending
      if (this.connectionRejector) {
        this.connectionRejector(new Error('WebSocket connection failed'));
        this.connectionResolver = null;
        this.connectionRejector = null;
      }
    };
  }

  private shouldReconnect(event: CloseEvent): boolean {
    // Don't reconnect for clean disconnects or if auto-reconnect is disabled
    if (!this.config.enableAutoReconnect || event.code === 1000) {
      return false;
    }
    
    // Don't reconnect if max attempts reached
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.setState(WebSocketState.FAILED);
      return false;
    }
    
    return true;
  }

  private attemptReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    
    const delay = this.calculateReconnectDelay();
    this.reconnectAttempts++;
    
    console.log(`🔄 Attempting reconnection ${this.reconnectAttempts}/${this.config.maxReconnectAttempts} in ${delay}ms`);
    
    this.reconnectTimeout = setTimeout(() => {
      if (this.endpoint && this.state === WebSocketState.RECONNECTING) {
        this.connect(this.endpoint).catch(error => {
          console.error('Reconnection failed:', error);
        });
      }
    }, delay);
  }

  private calculateReconnectDelay(): number {
    // Exponential backoff with jitter
    const baseDelay = this.config.reconnectInterval;
    const exponentialDelay = baseDelay * Math.pow(2, this.reconnectAttempts);
    const jitter = Math.random() * 0.3 * exponentialDelay; // 30% jitter
    return Math.min(exponentialDelay + jitter, 30000); // Cap at 30 seconds
  }

  private startHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
    
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: 'ping' });
      }
    }, this.config.heartbeatInterval);
  }

  private startMessageTimeoutMonitoring(): void {
    if (this.messageTimeout) {
      clearTimeout(this.messageTimeout);
    }
    
    const checkMessageTimeout = () => {
      const timeSinceLastMessage = Date.now() - this.lastMessageTime;
      
      if (timeSinceLastMessage > this.config.messageTimeout && this.isConnected()) {
        console.warn(`⚠️ No messages received for ${timeSinceLastMessage}ms, connection may be stale`);
        // Force reconnection
        this.ws?.close(1006, 'Message timeout');
      } else if (this.isConnected()) {
        // Schedule next check
        this.messageTimeout = setTimeout(checkMessageTimeout, this.config.messageTimeout);
      }
    };
    
    this.messageTimeout = setTimeout(checkMessageTimeout, this.config.messageTimeout);
  }

  private cleanup(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    
    if (this.messageTimeout) {
      clearTimeout(this.messageTimeout);
      this.messageTimeout = null;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    this.ws = null;
    this.connectionPromise = null;
  }

  private handleMessage(message: WebSocketMessage): void {
    // Handle system messages
    if (message.type === 'pong' || message.type === 'heartbeat') {
      return;
    }
    
    // Notify specific type handlers
    const handlers = this.messageHandlers.get(message.type) || [];
    handlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error(`Error in message handler for type ${message.type}:`, error);
      }
    });
    
    // Notify wildcard handlers
    const wildcardHandlers = this.messageHandlers.get('*') || [];
    wildcardHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('Error in wildcard message handler:', error);
      }
    });
  }

  private notifyError(error: Event | Error): void {
    this.errorHandlers.forEach(handler => {
      try {
        handler(error);
      } catch (err) {
        console.error('Error in error handler:', err);
      }
    });
  }

  private notifyStateChange(state: WebSocketState): void {
    this.stateChangeHandlers.forEach(handler => {
      try {
        handler(state);
      } catch (error) {
        console.error('Error in state change handler:', error);
      }
    });
  }

  /**
   * Add message handler for specific message type
   * Use '*' to handle all message types
   */
  addMessageHandler(type: string, handler: MessageHandler): void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    this.messageHandlers.get(type)!.push(handler);
  }

  removeMessageHandler(type: string, handler: MessageHandler): void {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  addErrorHandler(handler: ErrorHandler): void {
    this.errorHandlers.push(handler);
  }

  removeErrorHandler(handler: ErrorHandler): void {
    const index = this.errorHandlers.indexOf(handler);
    if (index > -1) {
      this.errorHandlers.splice(index, 1);
    }
  }

  addStateChangeHandler(handler: StateChangeHandler): void {
    this.stateChangeHandlers.push(handler);
  }

  removeStateChangeHandler(handler: StateChangeHandler): void {
    const index = this.stateChangeHandlers.indexOf(handler);
    if (index > -1) {
      this.stateChangeHandlers.splice(index, 1);
    }
  }

  /**
   * Send a message, automatically stringifying if needed
   */
  send(data: any): boolean {
    if (!this.isConnected()) {
      console.warn('Cannot send message: WebSocket not connected');
      return false;
    }
    
    try {
      const message = typeof data === 'string' ? data : JSON.stringify(data);
      this.ws!.send(message);
      return true;
    } catch (error) {
      console.error('Failed to send message:', error);
      return false;
    }
  }

  /**
   * Wait for connection to be established
   */
  async waitForConnection(timeout: number = 10000): Promise<void> {
    if (this.isConnected()) {
      return Promise.resolve();
    }
    
    if (this.connectionPromise) {
      return this.connectionPromise;
    }
    
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error('Connection timeout'));
      }, timeout);
      
      const checkConnection = () => {
        if (this.isConnected()) {
          clearTimeout(timeoutId);
          resolve();
        } else if (this.state === WebSocketState.FAILED) {
          clearTimeout(timeoutId);
          reject(new Error('Connection failed'));
        } else {
          setTimeout(checkConnection, 100);
        }
      };
      
      checkConnection();
    });
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  disconnect(): void {
    this.setState(WebSocketState.DISCONNECTED);
    this.cleanup();
    
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      try {
        this.ws.close(1000, 'Client disconnecting');
      } catch (error) {
        console.warn('Error closing WebSocket:', error);
      }
    }
    
    this.messageHandlers.clear();
    this.errorHandlers = [];
    this.stateChangeHandlers = [];
    this.reconnectAttempts = 0;
    this.endpoint = '';
  }
}

// Export a factory function for creating instances with specific configurations
export function createWebSocketService(config?: WebSocketConfig): EnhancedWebSocketService {
  return new EnhancedWebSocketService(config);
}