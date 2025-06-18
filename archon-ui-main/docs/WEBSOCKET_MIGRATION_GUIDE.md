# WebSocket Service Migration Guide

This guide helps migrate existing WebSocket implementations to use the EnhancedWebSocketService.

## Overview

The `EnhancedWebSocketService` provides:
- Connection state management
- Promise-based connection establishment
- Exponential backoff for reconnections
- Typed message handlers
- Heartbeat/keepalive support
- Better error handling and recovery

## Migration Steps

### 1. Import the Enhanced Service

```typescript
import { 
  EnhancedWebSocketService, 
  WebSocketState, 
  createWebSocketService 
} from './services/EnhancedWebSocketService';
```

### 2. Create Service Instance

Replace direct WebSocket creation with the enhanced service:

**Before:**
```typescript
const ws = new WebSocket(wsUrl);
ws.onopen = () => { ... };
ws.onmessage = (event) => { ... };
```

**After:**
```typescript
const wsService = createWebSocketService({
  maxReconnectAttempts: 5,
  reconnectInterval: 1000,
  heartbeatInterval: 30000,
  enableAutoReconnect: true
});

// Connect with promise
await wsService.connect('/api/endpoint');
```

### 3. Handle Messages with Type Safety

**Before:**
```typescript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'update') {
    handleUpdate(data);
  }
};
```

**After:**
```typescript
wsService.addMessageHandler('update', (message) => {
  handleUpdate(message.data);
});

// Or handle all messages
wsService.addMessageHandler('*', (message) => {
  console.log('Received:', message);
});
```

### 4. Monitor Connection State

```typescript
wsService.addStateChangeHandler((state: WebSocketState) => {
  switch (state) {
    case WebSocketState.CONNECTING:
      console.log('Connecting...');
      break;
    case WebSocketState.CONNECTED:
      console.log('Connected!');
      break;
    case WebSocketState.RECONNECTING:
      console.log('Reconnecting...');
      break;
    case WebSocketState.FAILED:
      console.log('Connection failed');
      break;
  }
});
```

### 5. Error Handling

```typescript
wsService.addErrorHandler((error) => {
  console.error('WebSocket error:', error);
  // Handle error appropriately
});
```

## Service-Specific Examples

### CrawlProgressService Migration

```typescript
class CrawlProgressServiceV2 {
  private webSocketService: EnhancedWebSocketService | null = null;

  async streamProgress(progressId: string, onMessage: ProgressCallback) {
    if (!this.webSocketService) {
      this.webSocketService = createWebSocketService({
        enableAutoReconnect: true,
        maxReconnectAttempts: 5
      });
    }

    // Connect to progress endpoint
    await this.webSocketService.connect(`/api/crawl-progress/${progressId}`);
    
    // Handle progress messages
    this.webSocketService.addMessageHandler('crawl_progress', (message) => {
      onMessage(message.data);
    });
  }
}
```

### AgentChatService Migration

```typescript
class AgentChatServiceV2 {
  private wsService: EnhancedWebSocketService;

  constructor() {
    this.wsService = createWebSocketService({
      heartbeatInterval: 20000,
      messageTimeout: 60000
    });
  }

  async connect(sessionId: string) {
    await this.wsService.connect(`/api/agent-chat/${sessionId}`);
    
    // Handle different message types
    this.wsService.addMessageHandler('chat_message', this.handleChatMessage);
    this.wsService.addMessageHandler('status_update', this.handleStatusUpdate);
    this.wsService.addMessageHandler('error', this.handleError);
  }

  sendMessage(message: string) {
    this.wsService.send({
      type: 'user_message',
      content: message
    });
  }
}
```

## Migration Checklist

- [ ] Replace WebSocket creation with EnhancedWebSocketService
- [ ] Convert callbacks to message handlers
- [ ] Add connection state monitoring
- [ ] Implement proper error handling
- [ ] Test reconnection behavior
- [ ] Update types for message handling
- [ ] Add connection verification before operations
- [ ] Clean up resources on component unmount

## Benefits After Migration

1. **Automatic Reconnection**: No need to manually implement reconnection logic
2. **Connection Verification**: Can wait for connection before sending messages
3. **Type Safety**: Strongly typed message handlers
4. **Better Error Handling**: Centralized error handling with callbacks
5. **State Management**: Know exactly what state the connection is in
6. **Resource Cleanup**: Proper cleanup prevents memory leaks

## Testing Migration

```typescript
// Test connection establishment
const wsService = createWebSocketService();
await wsService.connect('/api/test');
console.assert(wsService.isConnected(), 'Should be connected');

// Test message handling
let messageReceived = false;
wsService.addMessageHandler('test', () => {
  messageReceived = true;
});

// Test reconnection
// Simulate disconnect and verify automatic reconnection
```

## Gradual Migration Strategy

1. **Phase 1**: Migrate crawlProgressService (DONE ✅)
2. **Phase 2**: Migrate agentChatService
3. **Phase 3**: Migrate mcpService and related services
4. **Phase 4**: Migrate remaining services
5. **Phase 5**: Remove old WebSocket implementations

## Common Pitfalls to Avoid

1. **Not waiting for connection**: Always use `await` when connecting
2. **Forgetting to clean up**: Call `disconnect()` when done
3. **Multiple connections**: Reuse service instances when possible
4. **Ignoring state changes**: Monitor connection state for better UX
5. **Not handling errors**: Always add error handlers

## Support

For questions or issues during migration:
1. Check the EnhancedWebSocketService source code
2. Review the test examples
3. Look at completed migrations (crawlProgressServiceV2)