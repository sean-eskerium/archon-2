# Archon Python Test Suite Plan

This document outlines the complete test suite structure for the Archon Python backend. Each test file listed below includes specific test cases that need to be implemented.

## Test Directory Structure

```
tests/
├── conftest.py                    # Global test configuration and fixtures
├── unit/                          # Unit tests for individual components
│   ├── test_services/             # Service layer tests
│   ├── test_modules/              # MCP module tests
│   ├── test_utils/                # Utility function tests
│   └── test_models/               # Data model tests
├── integration/                   # Integration tests
│   ├── test_api/                  # API endpoint tests
│   ├── test_mcp/                  # MCP server integration tests
│   ├── test_websockets/           # WebSocket functionality tests
│   └── test_database/             # Database integration tests
├── e2e/                          # End-to-end tests
│   ├── test_workflows/            # Complete user workflows
│   └── test_mcp_tools/            # MCP tool execution flows
└── fixtures/                      # Test data and utilities
    ├── mock_data.py
    └── test_helpers.py
```

## Test Implementation Plan

### 🔴 Critical Priority Tests (Week 1)

#### Unit Tests - Services Layer

##### `tests/unit/test_services/test_project_service.py`
```python
# test_project_service_creates_project_with_valid_data
# test_project_service_validates_required_fields
# test_project_service_handles_duplicate_titles
# test_project_service_updates_project_fields
# test_project_service_deletes_project_cascades_tasks
# test_project_service_retrieves_project_by_id
# test_project_service_lists_projects_with_pagination
# test_project_service_filters_projects_by_status
```

##### `tests/unit/test_services/test_task_service.py`
```python
# test_task_service_creates_task_with_project_id
# test_task_service_validates_task_status_values
# test_task_service_creates_subtask_with_parent_id
# test_task_service_updates_task_status
# test_task_service_assigns_task_to_user
# test_task_service_filters_tasks_by_status
# test_task_service_filters_tasks_by_project
# test_task_service_archives_completed_tasks
# test_task_service_prevents_circular_subtask_references
# test_task_service_calculates_task_hierarchy
```

##### `tests/unit/test_services/test_document_service.py`
```python
# test_document_service_adds_document_to_project
# test_document_service_validates_document_type
# test_document_service_updates_document_content
# test_document_service_deletes_document_from_project
# test_document_service_lists_project_documents
# test_document_service_handles_document_metadata
# test_document_service_enforces_document_limits
```

##### `tests/unit/test_services/test_versioning_service.py`
```python
# test_versioning_creates_snapshot_of_jsonb_field
# test_versioning_tracks_change_history
# test_versioning_restores_previous_version
# test_versioning_lists_version_history
# test_versioning_limits_version_retention
# test_versioning_handles_large_jsonb_data
# test_versioning_validates_field_names
```

##### `tests/unit/test_services/test_credential_service.py`
```python
# test_credential_service_loads_from_database
# test_credential_service_sets_environment_variables
# test_credential_service_validates_required_keys
# test_credential_service_handles_missing_credentials
# test_credential_service_updates_credentials
# test_credential_service_encrypts_sensitive_values
```

##### `tests/unit/test_services/test_mcp_client_service.py`
```python
# test_mcp_client_connects_to_server
# test_mcp_client_handles_connection_errors
# test_mcp_client_executes_tools
# test_mcp_client_manages_multiple_connections
# test_mcp_client_reconnects_on_failure
# test_mcp_client_lists_available_tools
# test_mcp_client_validates_tool_arguments
# test_mcp_client_handles_tool_errors
```

#### Unit Tests - RAG Services

##### `tests/unit/test_services/test_crawling_service.py`
```python
# test_crawling_service_crawls_single_page
# test_crawling_service_extracts_content
# test_crawling_service_handles_invalid_urls
# test_crawling_service_respects_robots_txt
# test_crawling_service_limits_crawl_depth
# test_crawling_service_detects_content_type
# test_crawling_service_handles_redirects
# test_crawling_service_manages_concurrent_crawls
```

##### `tests/unit/test_services/test_document_storage_service.py`
```python
# test_storage_chunks_large_documents
# test_storage_generates_embeddings
# test_storage_stores_document_metadata
# test_storage_handles_duplicate_content
# test_storage_processes_different_file_types
# test_storage_validates_file_size_limits
# test_storage_extracts_text_from_pdf
# test_storage_handles_encoding_issues
```

##### `tests/unit/test_services/test_search_service.py`
```python
# test_search_finds_similar_documents
# test_search_applies_similarity_threshold
# test_search_filters_by_source
# test_search_reranks_results_when_enabled
# test_search_handles_empty_queries
# test_search_limits_result_count
# test_search_includes_metadata_in_results
# test_search_handles_special_characters
```

### 🟡 High Priority Tests (Week 1-2)

#### Integration Tests - API Endpoints

##### `tests/integration/test_api/test_projects_api.py`
```python
# test_create_project_endpoint_returns_201
# test_create_project_validates_input_schema
# test_get_project_returns_full_details
# test_list_projects_supports_pagination
# test_update_project_patches_fields
# test_delete_project_returns_204
# test_project_websocket_streams_updates
# test_project_api_requires_authentication
# test_project_api_handles_concurrent_updates
```

##### `tests/integration/test_api/test_knowledge_api.py`
```python
# test_upload_document_accepts_multipart_form
# test_upload_document_validates_file_types
# test_upload_document_returns_processing_status
# test_search_knowledge_returns_ranked_results
# test_search_knowledge_streams_progress
# test_crawl_website_initiates_async_task
# test_crawl_progress_websocket_updates
# test_delete_source_removes_all_pages
# test_knowledge_api_handles_large_files
```

##### `tests/integration/test_api/test_mcp_api.py`
```python
# test_mcp_status_returns_server_state
# test_start_mcp_server_spawns_process
# test_stop_mcp_server_terminates_process
# test_mcp_logs_websocket_streams_output
# test_mcp_api_prevents_duplicate_starts
# test_mcp_api_handles_server_crashes
```

##### `tests/integration/test_api/test_agent_chat_api.py`
```python
# test_create_chat_session_returns_session_id
# test_chat_websocket_accepts_messages
# test_chat_streams_ai_responses
# test_chat_maintains_conversation_history
# test_chat_executes_tool_calls
# test_chat_handles_session_timeout
# test_chat_supports_multiple_sessions
```

##### `tests/integration/test_api/test_settings_api.py`
```python
# test_get_settings_returns_current_values
# test_update_settings_persists_changes
# test_settings_validates_api_keys
# test_settings_hides_sensitive_values
# test_settings_handles_invalid_keys
# test_settings_triggers_service_reload
```

#### Integration Tests - MCP Server

##### `tests/integration/test_mcp/test_mcp_server_lifecycle.py`
```python
# test_mcp_server_initializes_with_tools
# test_mcp_server_handles_lifespan_events
# test_mcp_server_loads_all_modules
# test_mcp_server_creates_archon_context
# test_mcp_server_handles_initialization_errors
# test_mcp_server_cleans_up_resources
```

##### `tests/integration/test_mcp/test_mcp_tool_execution.py`
```python
# test_health_check_tool_returns_status
# test_session_info_tool_lists_sessions
# test_manage_project_tool_creates_project
# test_manage_task_tool_crud_operations
# test_perform_rag_query_searches_knowledge
# test_crawl_single_page_indexes_content
# test_tool_execution_handles_errors
# test_tool_execution_validates_params
```

### 🟢 Standard Priority Tests (Week 2)

#### Unit Tests - Modules and Utils

##### `tests/unit/test_modules/test_project_module.py`
```python
# test_project_module_registers_correct_tools
# test_project_module_tool_schemas_valid
# test_project_module_handles_service_errors
# test_project_module_formats_responses
```

##### `tests/unit/test_modules/test_rag_module.py`
```python
# test_rag_module_registers_search_tools
# test_rag_module_validates_search_params
# test_rag_module_handles_empty_results
# test_rag_module_formats_search_results
```

##### `tests/unit/test_utils/test_utils.py`
```python
# test_get_supabase_client_returns_singleton
# test_get_supabase_client_validates_url
# test_chunk_text_respects_size_limits
# test_chunk_text_maintains_overlap
# test_sanitize_input_removes_html
# test_format_timestamp_handles_timezones
```

##### `tests/unit/test_models/test_models.py`
```python
# test_project_model_validates_fields
# test_task_model_enforces_status_enum
# test_document_model_serializes_correctly
# test_model_relationships_defined
```

#### Integration Tests - WebSockets

##### `tests/integration/test_websockets/test_websocket_connections.py`
```python
# test_websocket_accepts_valid_connections
# test_websocket_rejects_invalid_tokens
# test_websocket_handles_disconnections
# test_websocket_broadcasts_to_rooms
# test_websocket_rate_limits_messages
```

##### `tests/integration/test_websockets/test_progress_streaming.py`
```python
# test_crawl_progress_streams_updates
# test_document_processing_progress
# test_test_execution_output_streaming
# test_progress_handles_errors_gracefully
```

### 🔵 Nice-to-Have Tests (Week 3)

#### End-to-End Tests

##### `tests/e2e/test_workflows/test_knowledge_workflow.py`
```python
# test_complete_document_upload_and_search_flow
# test_website_crawl_and_query_flow
# test_multi_source_rag_query_flow
```

##### `tests/e2e/test_workflows/test_project_workflow.py`
```python
# test_create_project_with_tasks_flow
# test_project_collaboration_flow
# test_task_assignment_and_completion_flow
```

##### `tests/e2e/test_mcp_tools/test_mcp_tool_chains.py`
```python
# test_project_creation_and_task_chain
# test_knowledge_indexing_and_search_chain
# test_cross_module_tool_execution
```

#### Performance Tests

##### `tests/performance/test_load_performance.py`
```python
# test_api_handles_concurrent_requests
# test_websocket_handles_multiple_connections
# test_search_performance_with_large_dataset
# test_document_upload_throughput
```

## Test Fixtures and Utilities

### `tests/fixtures/mock_data.py`
```python
# Sample projects, tasks, documents
# Mock API responses
# Test file content
# WebSocket message samples
```

### `tests/fixtures/test_helpers.py`
```python
# Database setup/teardown helpers
# Mock service factories
# WebSocket test client
# Authentication helpers
# File upload helpers
```

### `tests/conftest.py`
```python
# Global pytest fixtures
# Database session management
# Mock service providers
# Test client configuration
# Async test support
# Coverage configuration
```

## Coverage Goals

| Component | Target | Priority |
|-----------|--------|----------|
| Service Layer | 95% | Critical |
| API Endpoints | 90% | Critical |
| MCP Tools | 90% | Critical |
| Utils | 95% | High |
| Models | 100% | High |
| WebSockets | 85% | Medium |
| E2E Flows | 80% | Medium |

## Execution Order

1. **Week 1**: Critical service layer tests + credential/config tests
2. **Week 2**: API integration tests + MCP tool tests
3. **Week 3**: WebSocket tests + E2E workflows + performance tests

## Total Test Count

- **Unit Tests**: 78 test cases
- **Integration Tests**: 55 test cases
- **E2E Tests**: 8 test cases
- **Performance Tests**: 4 test cases
- **Total**: 145 test cases

This plan provides comprehensive coverage of the Archon Python backend, focusing on critical business logic first, then expanding to cover all user-facing functionality.