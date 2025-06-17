# Test Suite Refactoring Checklist

## Overview
This document provides a file-by-file checklist for implementing the test suite improvements identified in IMPLEMENTATION_PART_2.md.

## Infrastructure Files

### 1. `python/tests/pytest.ini` ✅
**Changes Required:**
- [ ] Add `minversion = 8.0`
- [ ] Update `addopts` with `-ra`, `--strict-markers`, `--import-mode=importlib`, `--tb=short`
- [ ] Add `testpaths = tests`
- [ ] Add explicit file/class/function patterns
- [ ] Expand markers with detailed descriptions
- [ ] Add `required_plugins` section
- [ ] Add timeout and flaky marker definitions

### 2. `python/tests/.coveragerc` ✅
**Changes Required:**
- [ ] Add `parallel = True` for pytest-xdist support
- [ ] Add `source_pkgs = src` for better path handling
- [ ] Add exclusion for performance test code
- [ ] Add context markers for different test types

### 3. `python/tests/conftest.py` (Root) ✅
**Changes Required:**
- [ ] Change key fixtures to session scope (config, embedding_model)
- [ ] Add autouse fixture to prevent network calls in unit tests
- [ ] Add memory tracker fixture
- [ ] Reorganize imports and add better documentation
- [ ] Add performance benchmark fixtures
- [ ] Add fixture factories for common data types

### 4. `python/tests/unit/conftest.py` (New File) ✅
**Changes Required:**
- [ ] Create file with unit-test specific fixtures
- [ ] Add mock fixtures that override integration fixtures
- [ ] Add autouse fixture for database isolation

### 5. `python/tests/integration/conftest.py` (New File) ✅
**Changes Required:**
- [ ] Create file with integration-test specific fixtures
- [ ] Add real database connection fixtures
- [ ] Add cleanup fixtures for test data

### 6. `python/tests/e2e/conftest.py` (New File) ✅
**Changes Required:**
- [ ] Create file with e2e-test specific fixtures
- [ ] Add fixtures for complete system setup
- [ ] Add fixtures for test user creation

## Test Helper Files

### 7. `python/tests/fixtures/mock_data.py` ✅
**Changes Required:**
- [ ] Convert static factory functions to fixture factories
- [ ] Add ID generation for better tracking
- [ ] Add cleanup tracking for created objects
- [ ] Add parametrized data generation

### 8. `python/tests/fixtures/test_helpers.py` ✅
**Changes Required:**
- [ ] Add memory tracking helpers
- [ ] Add performance benchmark helpers
- [ ] Add better async test helpers
- [ ] Add fixture request context helpers

## Unit Test Files - Services

### 9. `python/tests/unit/test_services/test_projects/test_project_service.py` ✅
**Changes Required:**
- [ ] Update fixture scope usage
- [ ] Add parametrization with custom IDs
- [ ] Enhance exception testing with regex matching
- [ ] Add performance markers to slow tests
- [ ] Use factory fixtures instead of static data

### 10. `python/tests/unit/test_services/test_projects/test_task_service.py` ✅
**Changes Required:**
- [ ] Add parametrized tests for status transitions
- [ ] Use indirect parametrization for complex setups
- [ ] Add timeout markers for WebSocket tests
- [ ] Improve exception assertions

### 11. `python/tests/unit/test_services/test_projects/test_document_service.py` ✅
**Changes Required:**
- [ ] Add parametrized tests for JSONB operations
- [ ] Use tmp_path fixture for file operations
- [ ] Add memory tracking for large documents
- [ ] Enhance version comparison tests

### 12. `python/tests/unit/test_services/test_credential_service.py` ✅
**Changes Required:**
- [ ] Add parametrized encryption tests
- [ ] Use monkeypatch.setenv instead of manual env manipulation
- [ ] Add security-focused markers
- [ ] Enhance error message assertions

### 13. `python/tests/unit/test_services/test_mcp_client_service.py` ✅
**Changes Required:**
- [ ] Add timeout markers for connection tests
- [ ] Use parametrized transport configurations
- [ ] Add flaky markers for reconnection tests
- [ ] Improve SSE event testing

### 14. `python/tests/unit/test_services/test_projects/test_versioning_service.py` ✅
**Changes Required:**
- [ ] Add parametrized diff generation tests
- [ ] Use factory fixtures for version data
- [ ] Add performance tests for large diffs
- [ ] Enhance restoration test assertions

### 15. `python/tests/unit/test_services/test_mcp_session_manager.py` ✅
**Changes Required:**
- [ ] Add parametrized session timeout tests
- [ ] Use indirect parametrization for session configs
- [ ] Add concurrent session tests
- [ ] Improve cleanup verification

### 16. `python/tests/unit/test_services/test_rag/test_crawling_service.py` ✅
**Changes Required:**
- [ ] Add timeout markers for crawl operations
- [ ] Use parametrized URL patterns
- [ ] Add retry logic with flaky markers
- [ ] Enhance robots.txt testing

### 17. `python/tests/unit/test_services/test_rag/test_document_storage_service.py` ✅
**Changes Required:**
- [ ] Add parametrized chunk size tests
- [ ] Use factory fixtures for documents
- [ ] Add memory tracking for embeddings
- [ ] Improve embedding generation tests

### 18. `python/tests/unit/test_services/test_rag/test_search_service.py` ✅
**Changes Required:**
- [ ] Add parametrized search query tests
- [ ] Add performance benchmarks
- [ ] Use indirect parametrization for search configs
- [ ] Enhance reranking tests

### 19. `python/tests/unit/test_utils/test_utils.py` ✅
**Changes Required:**
- [ ] Add parametrized embedding tests
- [ ] Use session-scoped fixtures for models
- [ ] Add performance markers
- [ ] Improve error handling tests

### 20. `python/tests/unit/test_services/test_prompt_service.py` ✅
**Changes Required:**
- [ ] Add parametrized prompt template tests
- [ ] Use factory fixtures for prompts
- [ ] Add caching verification tests
- [ ] Enhance singleton pattern tests

### 21. `python/tests/unit/test_services/test_rag/test_source_management_service.py` ✅
**Changes Required:**
- [ ] Add parametrized source type tests
- [ ] Use factory fixtures for sources
- [ ] Add concurrent access tests
- [ ] Improve metadata handling tests

## Unit Test Files - Agents

### 22. `python/tests/unit/test_agents/test_base_agent.py` ✅
**Changes Required:**
- [ ] Add timeout markers for streaming tests
- [ ] Use parametrized rate limit tests
- [ ] Add performance benchmarks
- [ ] Enhance error recovery tests

### 23. `python/tests/unit/test_agents/test_document_agent.py` ✅
**Changes Required:**
- [ ] Add parametrized conversation tests
- [ ] Use factory fixtures for messages
- [ ] Add memory usage tests
- [ ] Improve context handling tests

### 24. `python/tests/unit/test_agents/test_rag_agent.py` ✅
**Changes Required:**
- [ ] Add parametrized search integration tests
- [ ] Use indirect parametrization for configs
- [ ] Add performance tests
- [ ] Enhance retrieval tests

## Unit Test Files - APIs

### 25. `python/tests/unit/test_api/test_projects_api.py` ✅
**Changes Required:**
- [ ] Add parametrized endpoint tests
- [ ] Use factory fixtures for requests
- [ ] Add WebSocket timeout tests
- [ ] Improve error response tests

### 26. `python/tests/unit/test_api/test_settings_api.py` ✅
**Changes Required:**
- [ ] Add parametrized configuration tests
- [ ] Use monkeypatch for env vars
- [ ] Add validation tests
- [ ] Enhance credential tests

### 27. `python/tests/unit/test_api/test_knowledge_api.py` ✅
**Changes Required:**
- [ ] Add parametrized pagination tests
- [ ] Use factory fixtures for knowledge items
- [ ] Add performance tests for large datasets
- [ ] Improve filtering tests

### 28. `python/tests/unit/test_api/test_mcp_api.py` ✅
**Changes Required:**
- [ ] Add timeout markers for server operations
- [ ] Use parametrized server configs
- [ ] Add concurrent request tests
- [ ] Enhance log streaming tests

### 29. `python/tests/unit/test_api/test_agent_chat_api.py` ✅
**Changes Required:**
- [ ] Add WebSocket timeout tests
- [ ] Use parametrized message types
- [ ] Add rate limiting tests
- [ ] Improve streaming tests

### 30. `python/tests/unit/test_api/test_mcp_client_api.py` ✅
**Changes Required:**
- [ ] Add parametrized client management tests
- [ ] Use factory fixtures for clients
- [ ] Add health check performance tests
- [ ] Enhance error handling tests

### 31. `python/tests/unit/test_api/test_tests_api.py` ✅
**Changes Required:**
- [ ] Add timeout markers for test execution
- [ ] Use parametrized test scenarios
- [ ] Add streaming output tests
- [ ] Improve cancellation tests

## Unit Test Files - Modules and Core

### 32. `python/tests/unit/test_modules/test_project_module.py` ✅
**Changes Required:**
- [ ] Add parametrized MCP tool tests
- [ ] Use factory fixtures for projects
- [ ] Add performance tests
- [ ] Enhance error handling

### 33. `python/tests/unit/test_modules/test_rag_module.py` ✅
**Changes Required:**
- [ ] Add parametrized crawl tests
- [ ] Use indirect parametrization
- [ ] Add timeout markers
- [ ] Improve query tests

### 34. `python/tests/unit/test_config.py` ✅
**Changes Required:**
- [ ] Add parametrized env var tests
- [ ] Use monkeypatch extensively
- [ ] Add validation edge cases
- [ ] Enhance error messages

### 35. `python/tests/unit/test_models/test_mcp_models.py` ✅
**Changes Required:**
- [ ] Add parametrized validation tests
- [ ] Use factory fixtures for models
- [ ] Add serialization tests
- [ ] Improve error cases

### 36. `python/tests/unit/test_models/test_models.py` ✅
**Changes Required:**
- [ ] Add comprehensive validation tests
- [ ] Use parametrized field tests
- [ ] Add edge case handling
- [ ] Enhance type checking

### 37. `python/tests/unit/test_logfire_config.py` ✅
**Changes Required:**
- [ ] Add parametrized config tests
- [ ] Use monkeypatch for env vars
- [ ] Add performance impact tests
- [ ] Improve initialization tests

### 38. `python/tests/unit/test_main.py` ✅
**Changes Required:**
- [ ] Add startup/shutdown tests
- [ ] Use parametrized middleware tests
- [ ] Add error handling tests
- [ ] Enhance lifecycle tests

### 39. `python/tests/unit/test_mcp_server.py` ✅
**Changes Required:**
- [ ] Add timeout markers
- [ ] Use parametrized transport tests
- [ ] Add concurrent connection tests
- [ ] Improve message handling

## Integration Test Files

### 40. `python/tests/integration/test_database/test_database_integration.py` ✅
**Changes Required:**
- [ ] Use module-scoped database fixtures
- [ ] Add transaction rollback tests
- [ ] Add connection pool tests
- [ ] Enhance query performance tests

### 41. `python/tests/integration/test_mcp/test_mcp_integration.py` ✅
**Changes Required:**
- [ ] Add timeout markers
- [ ] Use parametrized server/client tests
- [ ] Add stress tests
- [ ] Improve lifecycle tests

## E2E Test Files

### 42. `python/tests/e2e/test_workflows/test_project_workflow.py` ✅
**Changes Required:**
- [ ] Add complete workflow tests
- [ ] Use factory fixtures
- [ ] Add performance benchmarks
- [ ] Enhance validation

### 43. `python/tests/e2e/test_workflows/test_rag_workflow.py` ✅
**Changes Required:**
- [ ] Add end-to-end crawl tests
- [ ] Use parametrized queries
- [ ] Add timeout markers
- [ ] Improve result validation

## Performance Test Files

### 44. `python/tests/performance/test_performance.py` ✅
**Changes Required:**
- [ ] Add benchmark fixtures
- [ ] Use parametrized load tests
- [ ] Add memory profiling
- [ ] Enhance scalability tests

## Utility Files

### 45. `python/tests/run_tests.py` ✅
**Changes Required:**
- [ ] Add marker-based test selection
- [ ] Add parallel execution support
- [ ] Add better reporting options
- [ ] Enhance CI/CD integration

## Priority Order

1. **Phase 1 - Infrastructure (Week 1)**
   - Files 1-8: Core configuration and fixtures

2. **Phase 2 - Critical Services (Week 2)**
   - Files 9-19: Core service tests

3. **Phase 3 - APIs and Agents (Week 3)**
   - Files 22-31: Agent and API tests

4. **Phase 4 - Advanced Tests (Week 4)**
   - Files 32-45: Modules, integration, E2E, performance

## Notes
- Each file should be updated incrementally
- Run tests after each change to ensure nothing breaks
- Update documentation as changes are made
- Consider creating a migration script for common changes