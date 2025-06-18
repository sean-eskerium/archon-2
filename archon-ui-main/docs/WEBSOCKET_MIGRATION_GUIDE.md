# WebSocket Service Migration Guide

This guide helps migrate existing WebSocket implementations to use the EnhancedWebSocketService.

## Current Migration Status

### ✅ Completed Migrations (High Priority)
- `crawlProgressServiceV2.ts` - Migrated to EnhancedWebSocketService
- `websocketService.ts` - Fully migrated (generic WebSocket wrapper and taskUpdateService)
- `agentChatService.ts` - Fully migrated with session management

### 🔄 Pending Migrations (Medium Priority)
- `mcpService.ts` - MCP logs streaming
- `mcpServerService.ts` - MCP server logs streaming  
- `projectService.ts` - Project WebSocket connection
- `projectCreationProgressService.ts` - Project creation progress
- `serverHealthService.ts` - Server health monitoring

### 📝 Low Priority (Can remain as-is)
- `testService.ts` - Test execution WebSocket
- `crawlProgressService.ts` - Original crawl progress (deprecated in favor of V2)

## Next Steps

### For Developers

1. **Use EnhancedWebSocketService for new features**
   - Import: `import { createWebSocketService } from './services/EnhancedWebSocketService'`
   - Never use `new WebSocket()` directly

2. **Follow the pattern from completed migrations**
   - See `websocketService.ts` for simple examples
   - See `agentChatService.ts` for complex session management

3. **Test WebSocket connections**
   - Use the patterns in `testing-vitest-strategy.mdx`
   - Always test reconnection scenarios

### For Remaining Migrations

If you need to migrate the remaining services:

1. **Start with `projectCreationProgressService.ts`**
   - Similar to crawlProgressServiceV2
   - Single connection per progress ID

2. **Then migrate MCP services**
   - `mcpService.ts` and `mcpServerService.ts`
   - Log streaming is straightforward

3. **Finally `serverHealthService.ts`**
   - Simple status monitoring
   - Consider if it really needs WebSocket

## Key Benefits of Migration

1. **Automatic Reconnection**: No manual reconnection logic needed
2. **Connection State Management**: Always know connection status
3. **Type Safety**: Strongly typed message handlers
4. **Consistent Error Handling**: Centralized error management
5. **Resource Cleanup**: Proper cleanup prevents memory leaks

## Documentation

- [WebSocket Communication Guide](../../docs/docs/websockets.mdx) - Simplified guide
- [UI Documentation](../../docs/docs/ui.mdx) - Frontend patterns
- [Testing Guide](../../docs/docs/testing-vitest-strategy.mdx) - WebSocket testing

## Migration Priority

1. **High Priority** (Core functionality)
   - `websocketService.ts` - Central WebSocket management
   - `taskUpdateService` - Real-time task updates
   - `agentChatService.ts` - Agent interactions

2. **Medium Priority** (Important features)
   - `projectCreationProgressService.ts` - Project creation flow
   - `serverHealthService.ts` - Health monitoring
   - `mcpService.ts` & `mcpServerService.ts` - MCP integration

3. **Low Priority** (Less critical)
   - `testService.ts` - Test execution
   - `crawlProgressService.ts` - Already has V2 replacement

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