# Archon Frontend Test Suite Guide

This comprehensive guide covers the testing strategy, implementation patterns, and best practices for the Archon frontend test suite.

## Table of Contents

1. [Overview](#overview)
2. [Test Architecture](#test-architecture)
3. [Testing Patterns](#testing-patterns)
4. [Component Testing](#component-testing)
5. [Service Testing](#service-testing)
6. [WebSocket Testing](#websocket-testing)
7. [Integration Testing](#integration-testing)
8. [Running Tests](#running-tests)
9. [Coverage Requirements](#coverage-requirements)
10. [CI/CD Integration](#ci-cd-integration)

## Overview

The Archon frontend test suite uses Vitest with React Testing Library to provide comprehensive coverage of the TypeScript/React codebase. Our testing philosophy emphasizes:

- **User-centric testing**: Test what users see and do, not implementation details
- **WebSocket safety**: All WebSocket functionality must be mocked to prevent breaking live connections
- **Type safety**: Leverage TypeScript for better test reliability
- **Fast feedback**: Prioritize unit tests for rapid development cycles

## Test Architecture

### Technology Stack

- **Test Runner**: Vitest
- **Testing Library**: React Testing Library
- **Mocking**: Vitest vi mocks
- **Assertions**: Vitest expect
- **Coverage**: V8 coverage provider

### Directory Structure

```
test/
├── components/          # Component tests
├── services/           # Service layer tests
├── pages/              # Page component tests
├── contexts/           # Context provider tests
├── hooks/              # Custom hook tests
├── lib/                # Utility function tests
├── integration/        # Integration tests
├── e2e/                # End-to-end tests
├── performance/        # Performance tests
├── fixtures/           # Test data and mocks
└── utils/              # Test utilities
```

## Testing Patterns

### AAA Pattern

All tests follow the Arrange-Act-Assert pattern:

```typescript
it('should handle user interaction', async () => {
  // Arrange
  const mockHandler = vi.fn()
  const user = userEvent.setup()
  
  // Act
  render(<Button onClick={mockHandler}>Click me</Button>)
  await user.click(screen.getByRole('button'))
  
  // Assert
  expect(mockHandler).toHaveBeenCalledOnce()
})
```

### Test File Naming

- Unit tests: `ComponentName.test.tsx` or `serviceName.test.ts`
- Integration tests: `feature-integration.test.ts`
- E2E tests: `user-journey.test.tsx`

### Test Description Naming

```typescript
describe('ComponentName', () => {
  it('should handle specific behavior when condition is met', () => {
    // Test implementation
  })
})
```

## Component Testing

### Basic Component Test

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MyComponent } from '@/components/MyComponent'

describe('MyComponent', () => {
  it('should render with props', () => {
    render(<MyComponent title="Test Title" />)
    expect(screen.getByText('Test Title')).toBeInTheDocument()
  })

  it('should handle user interaction', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    
    render(<MyComponent onSubmit={onSubmit} />)
    
    await user.type(screen.getByRole('textbox'), 'Test input')
    await user.click(screen.getByRole('button', { name: /submit/i }))
    
    expect(onSubmit).toHaveBeenCalledWith({ value: 'Test input' })
  })
})
```

### Testing with Context Providers

```typescript
import { renderWithProviders } from '@/test/utils/test-utils'

it('should access theme context', () => {
  const { container } = renderWithProviders(<ThemedComponent />)
  expect(container.firstChild).toHaveClass('dark')
})
```

### Testing Async Components

```typescript
it('should load data asynchronously', async () => {
  render(<AsyncDataComponent />)
  
  // Wait for loading to finish
  expect(screen.getByText(/loading/i)).toBeInTheDocument()
  
  // Wait for data to appear
  await waitFor(() => {
    expect(screen.getByText('Data loaded')).toBeInTheDocument()
  })
})
```

## Service Testing

### Basic Service Test

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '@/services/api'
import { projectService } from '@/services/projectService'

vi.mock('@/services/api')

describe('projectService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch projects with pagination', async () => {
    const mockProjects = [{ id: '1', title: 'Test Project' }]
    vi.mocked(api.get).mockResolvedValue({ data: mockProjects })

    const result = await projectService.getProjects({ page: 1, limit: 10 })

    expect(api.get).toHaveBeenCalledWith('/api/projects?page=1&limit=10')
    expect(result).toEqual(mockProjects)
  })

  it('should handle API errors gracefully', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('Network error'))

    await expect(projectService.getProjects()).rejects.toThrow('Network error')
  })
})
```

### Testing Services with WebSocket

```typescript
import { websocketService } from '@/services/websocketService'

vi.mock('@/services/websocketService', () => ({
  websocketService: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    subscribe: vi.fn(),
    send: vi.fn(),
    getConnectionState: vi.fn()
  }
}))

describe('Service with WebSocket', () => {
  it('should subscribe to WebSocket updates', () => {
    const callback = vi.fn()
    const unsubscribe = vi.fn()
    
    vi.mocked(websocketService.subscribe).mockReturnValue(unsubscribe)
    
    const service = new MyWebSocketService()
    service.subscribeToUpdates('channel', callback)
    
    expect(websocketService.subscribe).toHaveBeenCalledWith('channel', callback)
  })
})
```

## WebSocket Testing

### CRITICAL: WebSocket Safety Rules

1. **NEVER** create real WebSocket connections in tests
2. **ALWAYS** mock the websocketService module
3. **ALWAYS** clean up subscriptions in afterEach
4. **NEVER** include WebSocket instances in dependency arrays

### WebSocket Mock Setup

```typescript
// test/fixtures/websocketMocks.ts
export const createMockWebSocketService = () => ({
  connect: vi.fn(),
  disconnect: vi.fn(),
  subscribe: vi.fn((channel, callback) => {
    // Return unsubscribe function
    return vi.fn()
  }),
  send: vi.fn(),
  getConnectionState: vi.fn(() => 'connected'),
  waitForConnection: vi.fn(() => Promise.resolve()),
})

// In test file
import { createMockWebSocketService } from '@/test/fixtures/websocketMocks'

vi.mock('@/services/websocketService', () => ({
  websocketService: createMockWebSocketService()
}))
```

### Testing WebSocket Interactions

```typescript
it('should handle WebSocket messages', async () => {
  const mockCallback = vi.fn()
  let capturedCallback: Function

  vi.mocked(websocketService.subscribe).mockImplementation((channel, callback) => {
    capturedCallback = callback
    return vi.fn() // unsubscribe
  })

  render(<WebSocketComponent />)

  // Simulate WebSocket message
  act(() => {
    capturedCallback!({ type: 'update', data: { id: 1, status: 'complete' } })
  })

  await waitFor(() => {
    expect(screen.getByText('Status: complete')).toBeInTheDocument()
  })
})
```

## Integration Testing

### API Integration Test

```typescript
// test/integration/api-integration.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { setupServer } from 'msw/node'
import { rest } from 'msw'
import { api } from '@/services/api'

const server = setupServer(
  rest.get('/api/projects', (req, res, ctx) => {
    return res(ctx.json([{ id: '1', title: 'Test Project' }]))
  })
)

beforeAll(() => server.listen())
afterAll(() => server.close())

describe('API Integration', () => {
  it('should handle real API calls', async () => {
    const projects = await api.get('/api/projects')
    expect(projects.data).toHaveLength(1)
  })
})
```

### Component Integration Test

```typescript
it('should integrate multiple components', async () => {
  const user = userEvent.setup()
  
  render(
    <ProviderWrapper>
      <ProjectPage />
    </ProviderWrapper>
  )

  // Test user flow through multiple components
  await user.click(screen.getByRole('button', { name: /new project/i }))
  await user.type(screen.getByLabelText(/project name/i), 'My Project')
  await user.click(screen.getByRole('button', { name: /create/i }))

  await waitFor(() => {
    expect(screen.getByText('My Project')).toBeInTheDocument()
  })
})
```

## Running Tests

### Command Line Options

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test test/services/websocketService.test.ts

# Run tests matching pattern
npm test -- --grep "websocket"

# Run tests in UI mode
npm run test:ui

# Run only unit tests
npm test -- --grep "unit"

# Run integration tests
npm test -- --grep "integration"

# Debug a specific test
npm test -- --inspect-brk test/components/Button.test.tsx
```

### Test Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData.ts',
      ],
    },
  },
})
```

## Coverage Requirements

### Target Coverage Levels

| Component Type | Target | Current | Status |
|---------------|--------|---------|---------|
| Services | 90% | 25% | 🔴 Needs work |
| Pages | 85% | 75% | 🟡 Good progress |
| Components | 85% | 5% | 🔴 Needs work |
| Hooks | 90% | 0% | 🔴 Not started |
| Utils | 95% | 0% | 🔴 Not started |
| Overall | 80% | 15% | 🔴 In progress |

### Coverage Reports

```bash
# Generate coverage report
npm run test:coverage

# View HTML coverage report
open coverage/index.html

# Check coverage thresholds
npm run test:coverage -- --coverage.thresholds.lines=80
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/frontend-tests.yml
name: Frontend Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: archon-ui-main/package-lock.json
      
      - name: Install dependencies
        working-directory: ./archon-ui-main
        run: npm ci
      
      - name: Run linter
        working-directory: ./archon-ui-main
        run: npm run lint
      
      - name: Run type check
        working-directory: ./archon-ui-main
        run: npm run type-check
      
      - name: Run tests with coverage
        working-directory: ./archon-ui-main
        run: npm run test:coverage
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./archon-ui-main/coverage/coverage-final.json
          flags: frontend
          name: frontend-coverage
```

### Pre-commit Hooks

```json
// package.json
{
  "husky": {
    "hooks": {
      "pre-commit": "lint-staged"
    }
  },
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write",
      "vitest related --run"
    ]
  }
}
```

## Best Practices

### Do's

1. ✅ Test user behavior, not implementation
2. ✅ Use semantic queries (getByRole, getByLabelText)
3. ✅ Mock all external dependencies
4. ✅ Clean up after each test
5. ✅ Use userEvent for user interactions
6. ✅ Test error states and edge cases
7. ✅ Keep tests focused and isolated

### Don'ts

1. ❌ Don't test implementation details
2. ❌ Don't create real WebSocket connections
3. ❌ Don't make real API calls (except in integration tests)
4. ❌ Don't use querySelector or class selectors
5. ❌ Don't include functions in useCallback dependencies
6. ❌ Don't skip cleanup in tests
7. ❌ Don't write overly complex test setups

## Troubleshooting

### Common Issues

1. **WebSocket connection errors**
   - Ensure websocketService is properly mocked
   - Check that no real WebSocket instances are created

2. **Async test timeouts**
   - Use waitFor with appropriate timeout
   - Ensure all promises are awaited

3. **State update warnings**
   - Wrap state updates in act()
   - Use waitFor for async updates

4. **Memory leaks**
   - Clean up subscriptions in afterEach
   - Clear all mocks between tests

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [MSW for API Mocking](https://mswjs.io/)

This guide is a living document. Please update it as new patterns emerge or better practices are discovered.