# Test Code Analysis - Archon Python Backend

## Overview
This document analyzes the mismatches between the test implementation and the actual code after merging changes from main.

## Critical Issues Found

### 1. ProjectService Field Mismatches

**Issue**: The `ProjectFactory` in `mock_data.py` creates a field called `name` but the actual `ProjectService` expects `title`.

**Location**: 
- `python/tests/fixtures/mock_data.py` line 42
- `python/src/services/projects/project_service.py` expects `title` field

**Fix Applied**: Changed `name` to `title` in ProjectFactory and added missing fields (docs, features, data, github_repo)

### 2. Missing Fields in ProjectFactory

**Issue**: The actual `ProjectService` expects fields that aren't in the factory:
- `docs` (array)
- `features` (array) 
- `data` (array)
- `github_repo` (optional string)

**Location**: `python/tests/fixtures/mock_data.py` ProjectFactory

**Fix Applied**: Added all missing fields to ProjectFactory defaults

### 3. Async Method Mismatches in TaskService

**Issue**: Several TaskService methods are async but tests might not be handling them properly:
- `create_task` - async
- `update_task` - async
- `archive_task` - async

**Location**: `python/src/services/projects/task_service.py`

**Status**: Tests correctly use `@pytest.mark.asyncio` and `async def` for these methods ✓

### 4. TaskService Validation Methods

**Issue**: The actual TaskService has validation methods that aren't async:
- `validate_status(self, status: str) -> Tuple[bool, str]`
- `validate_assignee(self, assignee: str) -> Tuple[bool, str]`

**Location**: `python/src/services/projects/task_service.py` lines 41-51

**Status**: Tests correctly handle these as sync methods ✓

### 5. Missing WebSocket Broadcasting

**Issue**: TaskService methods try to import and use `task_update_manager` for WebSocket broadcasting

**Location**: `python/src/services/projects/task_service.py` lines 16-29

**Status**: Tests correctly mock this with `@patch('src.services.projects.task_service.get_task_update_manager')` ✓

### 6. DocumentService Test Issues

**Issue**: Test file references `include_content` parameter that doesn't exist in actual `list_documents` method

**Location**: 
- Test: `python/tests/unit/test_services/test_projects/test_document_service.py` line ~340
- Actual: `python/src/services/projects/document_service.py` line 81 - only takes `project_id`

**Fix Required**: Remove `include_content` parameter from test calls

### 7. DocumentService Expected Fields

**Actual DocumentService document structure**:
```python
{
    "id": str(uuid.uuid4()),
    "document_type": document_type,
    "title": title,
    "content": content or {},
    "tags": tags or [],
    "status": "draft",
    "version": "1.0"
}
```

**Status**: DocumentFactory seems to have different structure, needs alignment

### 8. CredentialService Async Methods

**All methods are async**:
- `load_all_credentials()`
- `get_credential()`
- `set_credential()` 
- `delete_credential()`
- `get_credentials_by_category()`
- `list_all_credentials()`

**Status**: Tests correctly use `@pytest.mark.asyncio` ✓

### 9. Error Message Assertions

**Issue**: Tests check for specific error messages that might not match actual implementation:
- Test expects: "Database connection error"
- Actual might be: "Connection failed"

**Location**: Various test files with error handling tests

### 10. Import Issues

**Issue**: Some imports in tests might not match actual module structure after merge

## Services Review Status

1. **ProjectService** ✅ - Reviewed and fixed field name issues
2. **TaskService** ✅ - Reviewed, mostly correct but need to verify field names
3. **DocumentService** ✅ - Reviewed, found test parameter issues
4. **VersioningService** - Need to review
5. **CredentialService** ✅ - Reviewed, tests look correct for async
6. **MCPClientService** - Need to review
7. **MCPSessionManager** - Need to review
8. **CrawlingService** - Need to review
9. **DocumentStorageService** - Need to review
10. **SearchService** - Need to review
11. **SourceManagementService** - Need to review
12. **PromptService** - Need to review

## API Endpoint Tests

Need to verify:
- All API endpoints match actual implementation
- Request/response schemas match
- Error responses match

## Next Steps

1. ~~Fix ProjectFactory field names~~ ✅ DONE
2. ~~Add missing fields to factories~~ ✅ DONE
3. Fix DocumentService test parameters (remove `include_content`)
4. Align DocumentFactory with actual document structure
5. Review remaining services (Versioning, MCP*, RAG services)
6. Update error message assertions to match actual implementations
7. Verify all async/sync method signatures match
8. Check all import paths are correct
9. Review API endpoint tests

## Test Execution Issues

When tests are run, they will likely fail due to:
1. ~~Field name mismatches (name vs title)~~ ✅ FIXED
2. ~~Missing required fields in test data~~ ✅ FIXED
3. Import errors if module structure changed
4. Error message assertion mismatches
5. Missing mock setups for new dependencies added during merge
6. DocumentService test using non-existent parameters
7. Possible field mismatches in other factories (Task, Document, etc.)