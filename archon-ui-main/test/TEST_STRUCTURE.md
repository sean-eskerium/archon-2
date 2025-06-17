# Archon Frontend Test Structure - File Creation Guide

This document shows the exact directory structure and files to create for the frontend test suite.

## Directory Structure to Create

```bash
# Create test directories
mkdir -p test/components/layouts
mkdir -p test/components/project-tasks
mkdir -p test/components/mcp
mkdir -p test/components/settings
mkdir -p test/components/knowledge-base
mkdir -p test/components/ui
mkdir -p test/components/animations
mkdir -p test/contexts
mkdir -p test/hooks
mkdir -p test/lib
mkdir -p test/integration
mkdir -p test/e2e
mkdir -p test/performance
mkdir -p test/fixtures
mkdir -p test/utils
```

## Complete File List

### Configuration & Setup Files

```
test/
├── setup.ts                                      ✅ # Test environment setup
├── README.md                                     ✅ # Testing guide
├── TEST_IMPLEMENTATION_STATUS.md                 ✅ # This tracking document
├── TEST_STRUCTURE.md                             ✅ # File structure guide
└── .coveragerc                                   📝 # Coverage configuration
```

### Service Layer Tests (Priority: CRITICAL)

```
test/services/
├── api.test.ts                                   ✅ # 3 tests
├── mcpService.test.ts                            ✅ # 4 tests
├── knowledgeBaseService.test.ts                  ✅ # 10 tests
├── websocketService.test.ts                      📝 # 15 tests
├── projectService.test.ts                        📝 # 12 tests
├── agentChatService.test.ts                      📝 # 15 tests
├── credentialsService.test.ts                    📝 # 10 tests
├── mcpClientService.test.ts                      📝 # 10 tests
├── mcpServerService.test.ts                      📝 # 10 tests
├── testService.test.ts                           📝 # 10 tests
├── crawlProgressService.test.ts                  📝 # 8 tests
└── projectCreationProgressService.test.ts        📝 # 8 tests
```

### Page Tests (Priority: CRITICAL)

```
test/pages/
├── MCPPage.test.tsx                              ✅ # 5 tests
├── KnowledgeBasePage.test.tsx                    ✅ # 15 tests
├── CrawlingProgress.test.tsx                     ✅ # 12 tests
├── ProjectPage.test.tsx                          📝 # 10 tests
└── SettingsPage.test.tsx                         📝 # 8 tests
```

### Component Tests - Layouts (Priority: HIGH)

```
test/components/layouts/
├── MainLayout.test.tsx                           📝 # 6 tests
├── SideNavigation.test.tsx                       📝 # 8 tests
└── KnowledgeChatPanel.test.tsx                   📝 # 6 tests
```

### Component Tests - Project Tasks (Priority: HIGH)

```
test/components/project-tasks/
├── TasksTab.test.tsx                             📝 # 12 tests
├── TaskTableView.test.tsx                        📝 # 10 tests
├── TaskBoardView.test.tsx                        📝 # 8 tests
├── DraggableTaskCard.test.tsx                    📝 # 6 tests
├── DocsTab.test.tsx                              📝 # 10 tests
├── DataTab.test.tsx                              📝 # 8 tests
├── FeaturesTab.test.tsx                          📝 # 8 tests
├── BlockNoteEditor.test.tsx                      📝 # 8 tests
├── VersionHistoryModal.test.tsx                  📝 # 6 tests
└── Tabs.test.tsx                                 📝 # 4 tests
```

### Component Tests - MCP (Priority: HIGH)

```
test/components/mcp/
├── MCPClients.test.tsx                           📝 # 10 tests
├── ClientCard.test.tsx                           📝 # 8 tests
└── ToolTestingPanel.test.tsx                     📝 # 7 tests
```

### Component Tests - Settings (Priority: HIGH)

```
test/components/settings/
├── APIKeysSection.test.tsx                       📝 # 8 tests
├── FeaturesSection.test.tsx                      📝 # 6 tests
├── RAGSettings.test.tsx                          📝 # 7 tests
├── TestStatus.test.tsx                           📝 # 10 tests
└── IDEGlobalRules.test.tsx                       📝 # 4 tests
```

### Component Tests - Other (Priority: HIGH)

```
test/components/
├── App.test.tsx                                  ✅ # 2 tests
├── CrawlingProgressCard.test.tsx                 📝 # 6 tests
├── ProjectCreationProgressCard.test.tsx          📝 # 6 tests
└── knowledge-base/
    └── KnowledgeTable.test.tsx                   📝 # 8 tests
```

### Component Tests - UI (Priority: MEDIUM)

```
test/components/ui/
├── Button.test.tsx                               📝 # 6 tests
├── Input.test.tsx                                📝 # 5 tests
├── Select.test.tsx                               📝 # 5 tests
├── Card.test.tsx                                 📝 # 4 tests
├── Badge.test.tsx                                📝 # 4 tests
├── Toggle.test.tsx                               📝 # 4 tests
└── ThemeToggle.test.tsx                          📝 # 4 tests
```

### Component Tests - Animations (Priority: MEDIUM)

```
test/components/animations/
└── Animations.test.tsx                           📝 # 5 tests
```

### Context Tests (Priority: HIGH)

```
test/contexts/
├── ThemeContext.test.tsx                         📝 # 4 tests
├── ToastContext.test.tsx                         📝 # 6 tests
└── SettingsContext.test.tsx                      📝 # 5 tests
```

### Hook Tests (Priority: HIGH)

```
test/hooks/
├── useNeonGlow.test.ts                           📝 # 6 tests
└── useStaggeredEntrance.test.ts                  📝 # 4 tests
```

### Utility Tests (Priority: HIGH)

```
test/lib/
├── utils.test.ts                                 📝 # 8 tests
└── task-utils.test.tsx                           📝 # 7 tests
```

### Integration Tests (Priority: MEDIUM)

```
test/integration/
├── websocket-integration.test.ts                 📝 # 6 tests
├── api-integration.test.ts                       📝 # 5 tests
├── mcp-integration.test.ts                       📝 # 5 tests
├── project-workflow.test.tsx                     📝 # 5 tests
├── knowledge-workflow.test.tsx                   📝 # 5 tests
├── settings-persistence.test.ts                  📝 # 5 tests
├── auth-flow.test.tsx                            📝 # 5 tests
└── error-handling.test.tsx                       📝 # 4 tests
```

### End-to-End Tests (Priority: LOW)

```
test/e2e/
├── project-management.test.tsx                   📝 # 5 tests
├── knowledge-base-flow.test.tsx                  📝 # 5 tests
├── mcp-server-lifecycle.test.tsx                 📝 # 5 tests
├── agent-chat-flow.test.tsx                      📝 # 5 tests
└── complete-user-journey.test.tsx                📝 # 5 tests
```

### Performance Tests (Priority: LOW)

```
test/performance/
├── render-performance.test.tsx                   📝 # 5 tests
├── websocket-load.test.ts                        📝 # 5 tests
└── large-data-sets.test.tsx                      📝 # 5 tests
```

### Test Utilities and Fixtures

```
test/fixtures/
├── factories.ts                                  📝 # Mock data factories
├── mockData.ts                                   📝 # Static test data
├── apiMocks.ts                                   📝 # API response mocks
└── websocketMocks.ts                             📝 # WebSocket event mocks
```

```
test/utils/
├── test-utils.tsx                                📝 # Custom render functions
├── mockHelpers.ts                                📝 # Mock setup helpers
├── websocketTestClient.ts                        📝 # WebSocket test utilities
└── asyncHelpers.ts                               📝 # Async test utilities
```

## Summary Statistics

- **Total Directories**: 16
- **Total Test Files**: 68
- **Already Implemented**: 7 files (✅)
- **To Be Implemented**: 61 files (📝)
- **Total Test Cases**: ~465
- **Critical Priority Tests**: 138 (30%)
- **High Priority Tests**: 220 (47%)
- **Medium Priority Tests**: 77 (17%)
- **Low Priority Tests**: 30 (6%)

## Implementation Order

### Week 1: Critical Infrastructure
1. **Day 1**: Create all directory structure
2. **Day 2-3**: Implement critical service tests (9 files, ~98 tests)
3. **Day 4-5**: Complete page tests (2 files, ~18 tests)

### Week 2: Core Components
1. **Day 1-2**: Layout & MCP components (6 files, ~45 tests)
2. **Day 3-4**: Project task components (10 files, ~80 tests)
3. **Day 5**: Settings components (5 files, ~35 tests)

### Week 3: Supporting Infrastructure
1. **Day 1**: Context & Hook tests (5 files, ~25 tests)
2. **Day 2**: Utility tests (2 files, ~15 tests)
3. **Day 3-4**: UI component tests (8 files, ~37 tests)
4. **Day 5**: Test utilities and fixtures setup

### Week 4: Integration & Polish
1. **Day 1-2**: Integration tests (8 files, ~40 tests)
2. **Day 3**: E2E tests (5 files, ~25 tests)
3. **Day 4**: Performance tests (3 files, ~15 tests)
4. **Day 5**: Coverage analysis and cleanup

## File Creation Script

```bash
#!/bin/bash
# Create all test files with basic structure

# Function to create test file with boilerplate
create_test_file() {
    local filepath=$1
    local testname=$(basename "$filepath" .test.tsx)
    testname=$(basename "$testname" .test.ts)
    
    mkdir -p $(dirname "$filepath")
    
    if [[ $filepath == *.tsx ]]; then
        cat > "$filepath" << EOF
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { $testname } from '@/$(dirname ${filepath#test/})/$testname'

describe('$testname', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should render correctly', () => {
    // TODO: Implement test
    expect(true).toBe(true)
  })
})
EOF
    else
        cat > "$filepath" << EOF
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { $testname } from '@/$(dirname ${filepath#test/})/$testname'

describe('$testname', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should work correctly', () => {
    // TODO: Implement test
    expect(true).toBe(true)
  })
})
EOF
    fi
}

# Create all test files
# Add create_test_file commands for each file...
```

## Coverage Configuration

```javascript
// vitest.config.ts additions
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/**/*.test.{ts,tsx}',
        'src/types/**',
        'src/env.d.ts',
      ],
      thresholds: {
        global: {
          statements: 80,
          branches: 75,
          functions: 80,
          lines: 80,
        },
      },
    },
  },
})
```

This structure provides comprehensive test coverage for the Archon frontend with clear priorities and implementation guidance.