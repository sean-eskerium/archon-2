# UI (React/TypeScript) Codebase Clean-Up Guide

## 1. Orphaned and Duplicate Files

### Potentially Unused Components
- **`MindMapView.tsx`** - Only 86 lines, appears isolated at component root level
- Check if actively used or experimental code that should be removed

### Duplicate WebSocket Implementations
- `websocketService.ts` provides a generic service
- Individual services implement their own WebSocket connections:
  - `crawlProgressService.ts` - creates new WebSocket
  - `agentChatService.ts` - creates new WebSocket
  - `mcpService.ts` - creates new WebSocket
  - `projectCreationProgressService.ts` - creates new WebSocket
  - `mcpServerService.ts` - creates new WebSocket
  - `projectService.ts` - creates new WebSocket
  - `testService.ts` - creates new WebSocket
- Should use the shared WebSocketService consistently

## 2. File Organization and Naming Issues

### Inconsistent Component Organization
Components are organized inconsistently:
- Some in subdirectories: `knowledge-base/`, `project-tasks/`, `mcp/`, `settings/`
- Others at root level: `CrawlingProgressCard.tsx`, `ProjectCreationProgressCard.tsx`
- `MindMapView.tsx` seems out of place at root level

### Service Naming Inconsistencies
- Most services use camelCase: `knowledgeBaseService.ts`, `projectService.ts`
- But files vary: `mcpService.ts` vs `mcpServerService.ts` vs `mcpClientService.ts`
- Unclear distinction between similar services

### Type Organization
- Types split between `types/` directory and inline in service files
- No clear pattern for when to use separate type files

## 3. Code Comments and Documentation

### Files Lacking Inline Documentation

#### Complex Components Without Comments
- **`TaskBoardView.tsx`** - Complex drag-and-drop logic needs explanation
- **`BlockNoteEditor.tsx`** - Editor integration needs setup documentation
- **`agentChatService.ts`** (792 lines) - Large file with complex WebSocket handling

#### Service Files Needing Documentation
- **`websocketService.ts`** - Generic implementation needs usage examples
- **`projectService.ts`** (759 lines) - Large file with many functions
- **`mcpService.ts`** (652 lines) - Complex MCP protocol handling

#### Hook Documentation
- Custom hooks in `hooks/` lack JSDoc comments explaining usage
- `useNeonGlow.ts` and `useStaggeredEntrance.ts` need examples

## 4. Code Hygiene Issues

### Commented-Out Code
Found numerous instances of commented code in test files:
- Test files have many inline comments that look like old code
- Should be removed or converted to proper test descriptions

### Long Files
Several files exceed 500 lines and should be split:
- `agentChatService.ts` - 792 lines
- `projectService.ts` - 759 lines  
- `mcpService.ts` - 652 lines
- `CrawlingProgressCard.tsx` - 627 lines

### Inconsistent Import Organization
- No consistent order for imports (React, libraries, local)
- Mix of absolute and relative imports
- Some use `@/` alias, others use relative paths

## 5. WebSocket Management Issues

### Fragmented WebSocket Handling
- Central `WebSocketService` class exists but isn't used consistently
- Each feature implements its own WebSocket connection
- No shared error handling or reconnection logic
- Risk of connection leaks and inconsistent behavior

### Missing WebSocket Best Practices
- No exponential backoff for reconnections
- No connection pooling or reuse
- No centralized connection state management
- Heartbeat implementation varies across services

## 6. State Management Concerns

### Context Overuse
Multiple contexts without clear hierarchy:
- `ThemeContext`
- `ToastContext`
- `SettingsContext`
- No global state management solution (Redux/Zustand)

### Prop Drilling
- Some components pass props through multiple levels
- Could benefit from component composition patterns

## 7. Component Patterns

### Inconsistent Component Structure
- Some use function declarations, others use arrow functions
- Mixed naming conventions for event handlers
- No consistent pattern for component file structure

### Missing Component Abstractions
- Duplicate modal patterns across components
- No shared form components
- Loading states implemented differently everywhere

## 8. Type Safety Issues

### Any Types and Type Assertions
- Several `any` types in service files
- Type assertions without validation
- Missing error type definitions

### Incomplete Type Coverage
- WebSocket message types not fully defined
- API response types sometimes use inline definitions
- No shared error response types

## 9. Testing Gaps

### Test Organization
- Tests in `test/` directory but incomplete coverage
- Mock patterns inconsistent across test files
- No integration tests for WebSocket functionality

### Missing Test Utils
- No shared test utilities
- WebSocket mocking is ad-hoc
- No consistent pattern for mocking services

## 10. Performance Considerations

### Missing Optimizations
- No React.memo usage on expensive components
- useCallback/useMemo not used consistently
- Large components could benefit from code splitting

### Bundle Size Concerns
- Importing entire libraries instead of specific functions
- No lazy loading for heavy components
- Large service files increase initial bundle

## 11. Styling Issues

### Mixed Styling Approaches
- Tailwind classes mixed with CSS modules
- Some inline styles in components
- Custom CSS files in `styles/` not consistently used

### Inconsistent Spacing and Layout
- No consistent spacing system
- Some components use pixels, others use Tailwind units
- Responsive design not systematic

## 12. Recommendations Priority

### High Priority
1. Consolidate all WebSocket connections to use WebSocketService
2. Split large service files (>500 lines) into smaller modules
3. Remove all commented-out code
4. Establish consistent import organization

### Medium Priority
1. Reorganize components into consistent folder structure
2. Add comprehensive TypeScript types for all API responses
3. Create shared component library for common patterns
4. Implement proper error boundaries

### Low Priority
1. Add JSDoc comments to all exported functions
2. Implement consistent testing patterns
3. Optimize bundle size with code splitting
4. Standardize component patterns and naming

### Quick Wins
1. Delete `MindMapView.tsx` if unused
2. Fix import paths to consistently use `@/` alias
3. Add `.prettierrc` for consistent formatting
4. Create shared WebSocket types

## Code Standards Recommendations

### File Structure Template
```typescript
// 1. Imports (React first, then libraries, then local)
// 2. Types/Interfaces
// 3. Constants
// 4. Component/Function
// 5. Exports
```

### Naming Conventions
- Components: PascalCase
- Services: camelCase with 'Service' suffix
- Hooks: camelCase with 'use' prefix
- Types: PascalCase with descriptive names
- Event handlers: handle[Event] pattern

### Service Pattern
```typescript
class ServiceName {
  private static instance: ServiceName;
  
  static getInstance(): ServiceName {
    // Singleton pattern for services
  }
  
  // Consistent error handling
  // Proper typing
  // Clear method names
}
```