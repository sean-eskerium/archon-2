# Python Codebase Clean-Up Guide

## 1. Orphaned and Duplicate Files

### Orphaned Directory
- **`old_rag/`** - Contains old implementations that should be reviewed and either:
  - Migrated to the new structure if still useful
  - Documented as deprecated/reference code
  - Removed if no longer needed
  - Files: `crawl4ai_mcp.py` (1054 lines), `utils.py` (738 lines)

### Duplicate Functionality
- **`utils.py`** exists in both `src/` and `old_rag/` - consolidate or clarify purpose
- Multiple WebSocket managers across different API modules doing similar things:
  - `ConnectionManager` in `knowledge_api.py`
  - `CrawlProgressManager` in `knowledge_api.py`
  - `ProjectCreationProgressManager` in `projects_api.py`
  - `TaskUpdateManager` in `projects_api.py`
  - `ProjectListConnectionManager` in `projects_api.py`
  - `TestWebSocketManager` in `tests_api.py`
  - Consider creating a generic WebSocket manager base class

## 2. File Organization and Naming Issues

### Inconsistent Module Naming
- API modules use underscore naming: `mcp_api.py`, `agent_chat_api.py`
- Consider grouping related APIs (e.g., all MCP-related APIs in an `mcp/` subdirectory)

### Service Organization
- Services are split between `src/services/` and functionality in `src/api/`
- Some services have managers in API files instead of service files
- Consider clearer separation: API layer for HTTP endpoints, Service layer for business logic

### Scattered MCP Functionality
- MCP-related code is spread across:
  - `mcp_server.py` (main server)
  - `mcp_api.py` (API endpoints)
  - `mcp_client_api.py` (client management)
  - `services/mcp_client_service.py`
  - `services/mcp_session_manager.py`
  - Consider consolidating under `src/mcp/` directory

## 3. Code Comments and Documentation

### Files Needing Better Inline Documentation

#### `utils.py` (1119 lines)
- Complex embedding functions lack explanation of parameters and algorithm
- No docstrings for most functions
- Magic numbers (e.g., retry counts, delays) should be explained

#### `mcp_server.py`
- Missing high-level architecture comments
- Tool registration logic needs explanation
- Connection handling could use flow documentation

#### `credential_service.py`
- Encryption/decryption logic needs security notes
- Missing explanation of the credential loading lifecycle
- No comments on error handling strategy

#### Complex Functions Needing Comments
- `create_contextual_embeddings()` - algorithm explanation needed
- `search_documents_rpc()` - complex filtering logic uncommented
- `insert_batch_with_retry()` - retry strategy not documented

## 4. Code Hygiene Issues

### Excessive Print Statements
Found 74+ print statements that should use proper logging:
- **`old_rag/utils.py`** - 30+ print statements
- **`startup.py`** - 40+ print statements for startup messages
- **`agents/base_agent.py`** - Debug prints in error handling
- **`api/agent_chat_api.py`** - Extensive DEBUG print statements

### TODO Comments Without Tracking
- `mcp_server.py` line 1: Large TODO about error handling, connection pooling, etc.
- `utils.py` line 371: TODO about passing cached API key
- No consistent TODO format or tracking system

### Hardcoded Debug Code
- `api/mcp_api.py` has debug placeholder tools (lines 618-642)
- Debug endpoints like `/debug/token-usage` in production code
- Temporary debug logging that should be removed or controlled by log level

## 5. Error Handling Patterns

### Inconsistent Error Handling
- Some functions use try/except with generic Exception
- Others have specific exception types
- No consistent error response format across APIs

### Missing Error Context
- Many caught exceptions don't include original context
- Stack traces are often swallowed
- No consistent error logging pattern

## 6. Configuration and Constants

### Scattered Configuration
- Database config in environment variables
- Model configurations hardcoded in various files
- No central configuration management

### Magic Numbers
- Retry counts: 3, 5 (inconsistent across files)
- Batch sizes: 10, 50, 100 (no explanation)
- Timeouts: various values without documentation

## 7. Testing Gaps

### Test Organization
- Tests in `tests/` but also test-like code in API files
- No clear unit vs integration test separation
- Mock implementations scattered in test files

## 8. Security Concerns

### Credential Handling
- Print statements that might leak sensitive data
- API keys visible in debug logs (even truncated)
- No audit logging for credential access

## 9. Performance Issues

### Potential Memory Leaks
- WebSocket connections might not be properly cleaned up
- Large string concatenations in logging
- No connection pooling for database

### Inefficient Patterns
- Multiple database queries that could be batched
- Synchronous operations that could be async
- No caching strategy for frequently accessed data

## 10. Recommendations Priority

### High Priority
1. Remove all print statements, use structured logging
2. Consolidate WebSocket manager implementations
3. Clean up `old_rag/` directory
4. Remove debug code from production

### Medium Priority
1. Reorganize MCP-related code into dedicated directory
2. Add comprehensive docstrings to complex functions
3. Implement consistent error handling pattern
4. Create base classes for common patterns (WebSocket, API responses)

### Low Priority
1. Standardize configuration management
2. Improve test organization
3. Add performance monitoring
4. Document magic numbers and constants