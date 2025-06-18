# Archon React UI Test Structure - File Creation Guide

This document shows the exact directory structure and files to create for the Vitest test suite.

## Directory Structure to Create

```bash
# Create directories
mkdir -p test/unit/components/ui
mkdir -p test/unit/components/layouts
mkdir -p test/unit/components/knowledge-base
mkdir -p test/unit/components/mcp
mkdir -p test/unit/components/project-tasks
mkdir -p test/unit/components/settings
mkdir -p test/unit/components/animations
mkdir -p test/unit/pages
mkdir -p test/unit/services
mkdir -p test/unit/hooks
mkdir -p test/unit/contexts
mkdir -p test/unit/utils
mkdir -p test/integration/pages
mkdir -p test/integration/api
mkdir -p test/integration/websockets
mkdir -p test/e2e/workflows
mkdir -p test/fixtures/mocks
```

## Complete File List

### Configuration Files

```
test/
├── setup.ts                                      # Global test configuration
├── vitest.config.ts                             # Vitest configuration
└── tsconfig.json                                # TypeScript config for tests
```

### Unit Tests - Pages (Priority: CRITICAL)

```
test/unit/pages/
├── KnowledgeBasePage.test.tsx                   # 13 tests
├── ProjectPage.test.tsx                         # 11 tests
├── SettingsPage.test.tsx                        # 10 tests
└── MCPPage.test.tsx                             # 9 tests
```

### Unit Tests - Services (Priority: CRITICAL)

```
test/unit/services/
├── websocketService.test.ts                     # 7 tests
├── api.test.ts                                  # 6 tests
├── knowledgeBaseService.test.ts                 # 7 tests
├── projectService.test.ts                       # 8 tests
├── crawlProgressService.test.ts                 # 5 tests
├── credentialsService.test.ts                   # 4 tests
├── mcpService.test.ts                           # 6 tests
├── mcpClientService.test.ts                     # 5 tests
├── mcpServerService.test.ts                     # 4 tests
├── agentChatService.test.ts                     # 5 tests
├── projectCreationProgressService.test.ts       # 4 tests
└── testService.test.ts                          # 4 tests
```

### Unit Tests - UI Components (Priority: HIGH)

```
test/unit/components/ui/
├── Button.test.tsx                              # 6 tests
├── Input.test.tsx                               # 6 tests
├── Card.test.tsx                                # 4 tests
├── Badge.test.tsx                               # 4 tests
├── Select.test.tsx                              # 5 tests
├── Toggle.test.tsx                              # 4 tests
└── ThemeToggle.test.tsx                         # 3 tests
```

### Unit Tests - Layout Components (Priority: HIGH)

```
test/unit/components/layouts/
├── MainLayout.test.tsx                          # 4 tests
├── SideNavigation.test.tsx                      # 5 tests
└── ArchonChatPanel.test.tsx                     # 8 tests
```

### Unit Tests - Knowledge Components (Priority: HIGH)

```
test/unit/components/knowledge-base/
└── KnowledgeTable.test.tsx                      # 6 tests
```

### Unit Tests - MCP Components (Priority: MEDIUM)

```
test/unit/components/mcp/
├── ClientCard.test.tsx                          # 4 tests
├── MCPClients.test.tsx                          # 5 tests
└── ToolTestingPanel.test.tsx                    # 5 tests
```

### Unit Tests - Project Components (Priority: HIGH)

```
test/unit/components/project-tasks/
├── TaskBoardView.test.tsx                       # 6 tests
├── TaskTableView.test.tsx                       # 5 tests
├── DraggableTaskCard.test.tsx                   # 4 tests
├── BlockNoteEditor.test.tsx                     # 5 tests
├── Tabs.test.tsx                                # 3 tests
├── FeaturesTab.test.tsx                         # 4 tests
├── DocsTab.test.tsx                             # 5 tests
├── DataTab.test.tsx                             # 4 tests
└── VersionHistoryModal.test.tsx                 # 4 tests
```

### Unit Tests - Settings Components (Priority: MEDIUM)

```
test/unit/components/settings/
├── APIKeysSection.test.tsx                      # 4 tests
├── FeaturesSection.test.tsx                     # 3 tests
├── IDEGlobalRules.test.tsx                      # 4 tests
├── RAGSettings.test.tsx                         # 5 tests
└── TestStatus.test.tsx                          # 4 tests
```

### Unit Tests - Progress Components (Priority: MEDIUM)

```
test/unit/components/
├── CrawlingProgressCard.test.tsx                # 5 tests
└── ProjectCreationProgressCard.test.tsx         # 4 tests
```

### Unit Tests - Hooks (Priority: MEDIUM)

```
test/unit/hooks/
├── useNeonGlow.test.ts                          # 4 tests
└── useStaggeredEntrance.test.ts                 # 4 tests
```

### Unit Tests - Contexts (Priority: HIGH)

```
test/unit/contexts/
├── ToastContext.test.tsx                        # 5 tests
├── ThemeContext.test.tsx                        # 4 tests
└── SettingsContext.test.tsx                     # 4 tests
```

### Unit Tests - Utils (Priority: MEDIUM)

```
test/unit/utils/
├── utils.test.ts                                # 3 tests
├── projectSchemas.test.ts                       # 4 tests
└── task-utils.test.tsx                          # 5 tests
```

### Integration Tests - API (Priority: HIGH)

```
test/integration/api/
├── knowledge-api.test.ts                        # 5 tests
├── project-api.test.ts                          # 4 tests
├── mcp-api.test.ts                              # 4 tests
└── settings-api.test.ts                         # 3 tests
```

### Integration Tests - WebSockets (Priority: CRITICAL)

```
test/integration/websockets/
├── crawl-progress.test.ts                       # 5 tests
├── project-updates.test.ts                      # 4 tests
├── chat-websocket.test.ts                       # 4 tests
└── mcp-logs.test.ts                             # 3 tests
```

### Integration Tests - Pages (Priority: MEDIUM)

```
test/integration/pages/
├── knowledge-page-integration.test.tsx          # 4 tests
└── project-page-integration.test.tsx            # 4 tests
```

### End-to-End Tests (Priority: LOW)

```
test/e2e/workflows/
├── knowledge-workflow.test.ts                   # 3 tests
├── project-workflow.test.ts                     # 3 tests
└── mcp-workflow.test.ts                         # 2 tests
```

### Test Fixtures and Utilities

```
test/fixtures/
├── mocks/
│   ├── handlers.ts                             # MSW request handlers
│   ├── server.ts                               # MSW server setup
│   └── websocket-mocks.ts                      # WebSocket mock handlers
├── test-data.ts                                # Sample test data
├── test-utils.tsx                              # Custom render utilities
└── component-mocks.tsx                         # Mock component factories
```

## Test File Templates

### Component Test Template

```typescript
// test/unit/components/ui/Button.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from '@/components/ui/Button'

describe('Button', () => {
  it('renders button with correct variant', () => {
    render(<Button variant="primary">Click me</Button>)
    const button = screen.getByRole('button', { name: /click me/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('primary')
  })

  it('handles click events', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()
    
    render(<Button onClick={handleClick}>Click me</Button>)
    await user.click(screen.getByRole('button'))
    
    expect(handleClick).toHaveBeenCalledOnce()
  })
})
```

### Service Test Template

```typescript
// test/unit/services/api.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { api } from '@/services/api'

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      },
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn()
    }))
  }
}))

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('configures axios with base URL', () => {
    expect(axios.create).toHaveBeenCalledWith(
      expect.objectContaining({
        baseURL: expect.any(String)
      })
    )
  })
})
```

### WebSocket Test Template

```typescript
// test/integration/websockets/crawl-progress.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import WS from 'vitest-websocket-mock'
import { crawlProgressService } from '@/services/crawlProgressService'

describe('Crawl Progress WebSocket', () => {
  let server: WS

  beforeEach(async () => {
    server = new WS('ws://localhost:8080/api/crawl/progress')
  })

  afterEach(() => {
    WS.clean()
  })

  it('connects to progress stream', async () => {
    const progressId = 'test-123'
    const onProgress = vi.fn()
    
    crawlProgressService.streamProgress(progressId, onProgress)
    await server.connected
    
    expect(server).toHaveReceivedMessages([
      expect.stringContaining(progressId)
    ])
  })
})
```

## Summary Statistics

- **Total Directories**: 24
- **Total Test Files**: 73
- **Total Test Cases**: 151
- **Critical Priority Tests**: 69 (46%)
- **High Priority Tests**: 56 (37%)
- **Medium Priority Tests**: 21 (14%)
- **Low Priority Tests**: 5 (3%)

## Implementation Order

1. **Day 1-2**: Create directory structure and configuration files
2. **Week 1**: Implement critical page and service tests (69 tests)
3. **Week 2**: Implement UI components and integration tests (56 tests)
4. **Week 3**: Implement remaining unit tests and E2E (26 tests)

## Special Testing Considerations

### WebSocket Testing
- Use `vitest-websocket-mock` for WebSocket testing
- Test connection, reconnection, and message handling
- Mock server responses for different scenarios

### Component Testing
- Use React Testing Library for user-centric tests
- Mock external dependencies with MSW
- Test accessibility with `@testing-library/jest-dom`

### State Management Testing
- Test context providers with custom wrapper utilities
- Verify state updates and persistence
- Test error boundaries and edge cases

This structure provides complete test coverage for the Archon React UI with clear priorities and implementation guidance.