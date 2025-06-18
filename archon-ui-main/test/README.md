# Archon React UI Test Suite Plan

This document outlines the complete test suite structure for the Archon React/TypeScript frontend. Each test file listed below includes specific test cases that need to be implemented using Vitest and React Testing Library.

## Test Directory Structure

```
test/
├── setup.ts                       # Global test setup and configuration
├── unit/                          # Unit tests for individual components
│   ├── components/                # Component tests
│   │   ├── ui/                   # Base UI components
│   │   ├── layouts/              # Layout components
│   │   ├── knowledge-base/       # Knowledge components
│   │   ├── mcp/                  # MCP components
│   │   ├── project-tasks/        # Project components
│   │   └── settings/             # Settings components
│   ├── hooks/                     # Custom hook tests
│   ├── services/                  # Service layer tests
│   ├── contexts/                  # Context provider tests
│   └── utils/                     # Utility function tests
├── integration/                   # Integration tests
│   ├── pages/                     # Page-level tests
│   ├── api/                       # API integration tests
│   └── websockets/                # WebSocket tests
├── e2e/                          # End-to-end tests
│   └── workflows/                 # Complete user workflows
└── fixtures/                      # Test data and utilities
    ├── mocks/
    │   ├── handlers.ts            # MSW request handlers
    │   └── server.ts              # MSW server setup
    ├── test-data.ts               # Sample test data
    └── test-utils.tsx             # Custom render utilities
```

## Test Implementation Plan

### 🔴 Critical Priority Tests (Week 1)

#### Unit Tests - Pages

##### `test/unit/pages/KnowledgeBasePage.test.tsx`
```typescript
// test_renders_knowledge_base_page_with_loading_state
// test_switches_between_grid_and_table_view
// test_filters_items_by_knowledge_type
// test_searches_items_with_debounce
// test_groups_items_by_domain_in_grid_view
// test_handles_websocket_connection_and_updates
// test_displays_crawling_progress_cards
// test_deletes_single_knowledge_item
// test_deletes_grouped_knowledge_items
// test_opens_add_knowledge_modal
// test_handles_file_upload_progress
// test_validates_url_before_crawling
// test_retries_failed_crawl_operations
```

##### `test/unit/pages/ProjectPage.test.tsx`
```typescript
// test_renders_project_list_on_load
// test_creates_new_project_with_form
// test_selects_project_and_loads_tasks
// test_switches_between_task_views
// test_displays_task_board_with_columns
// test_displays_task_table_with_sorting
// test_manages_features_tab_content
// test_manages_docs_tab_with_editor
// test_manages_data_tab_with_json
// test_tracks_version_history
// test_handles_github_integration
```

##### `test/unit/pages/SettingsPage.test.tsx`
```typescript
// test_toggles_projects_feature_flag
// test_saves_openai_api_key_encrypted
// test_validates_api_key_format
// test_toggles_rag_settings_options
// test_runs_python_tests_with_streaming
// test_runs_react_tests_locally
// test_displays_test_output_realtime
// test_switches_test_view_modes
// test_collapses_test_section_by_default
// test_shows_toast_notifications
```

##### `test/unit/pages/MCPPage.test.tsx`
```typescript
// test_displays_mcp_server_status
// test_starts_and_stops_mcp_server
// test_streams_server_logs_via_websocket
// test_displays_available_tools_list
// test_tests_mcp_tools_interactively
// test_validates_tool_parameters
// test_copies_mcp_configuration
// test_manages_mcp_clients_crud
// test_handles_connection_errors
```

#### Unit Tests - Services (Critical)

##### `test/unit/services/websocketService.test.ts`
```typescript
// test_connects_to_websocket_endpoint
// test_handles_reconnection_on_disconnect
// test_manages_event_listeners
// test_removes_event_listeners_on_cleanup
// test_handles_connection_errors
// test_implements_exponential_backoff
// test_queues_messages_when_disconnected
```

##### `test/unit/services/api.test.ts`
```typescript
// test_configures_axios_with_base_url
// test_adds_request_interceptors
// test_adds_response_interceptors
// test_handles_401_unauthorized_errors
// test_handles_network_errors
// test_formats_error_messages
```

##### `test/unit/services/knowledgeBaseService.test.ts`
```typescript
// test_fetches_knowledge_items_with_params
// test_uploads_document_with_progress
// test_crawls_url_with_validation
// test_deletes_knowledge_item
// test_searches_knowledge_base
// test_manages_sources
// test_handles_api_errors
```

##### `test/unit/services/projectService.test.ts`
```typescript
// test_creates_project_with_validation
// test_fetches_project_list
// test_updates_project_details
// test_manages_tasks_crud_operations
// test_updates_task_status
// test_filters_tasks_by_criteria
// test_transforms_task_statuses
// test_handles_websocket_updates
```

### 🟡 High Priority Tests (Week 1-2)

#### Unit Tests - UI Components

##### `test/unit/components/ui/Button.test.tsx`
```typescript
// test_renders_button_variants
// test_applies_accent_colors
// test_handles_loading_state
// test_handles_disabled_state
// test_fires_onclick_events
// test_renders_with_icons
```

##### `test/unit/components/ui/Input.test.tsx`
```typescript
// test_renders_input_with_label
// test_displays_error_messages
// test_handles_value_changes
// test_shows_placeholder_text
// test_renders_with_icon
// test_applies_accent_colors
```

##### `test/unit/components/ui/Toggle.test.tsx`
```typescript
// test_toggles_checked_state
// test_fires_onchange_events
// test_handles_disabled_state
// test_applies_custom_styles
```

##### `test/unit/components/ui/Card.test.tsx`
```typescript
// test_renders_card_with_content
// test_applies_accent_color_borders
// test_handles_hover_effects
// test_composes_child_elements
```

#### Unit Tests - Complex Components

##### `test/unit/components/layouts/ArchonChatPanel.test.tsx`
```typescript
// test_renders_chat_interface
// test_handles_resize_functionality
// test_connects_to_websocket
// test_streams_ai_responses
// test_displays_message_history
// test_handles_tool_execution
// test_shows_connection_status
// test_handles_errors_gracefully
```

##### `test/unit/components/knowledge-base/KnowledgeTable.test.tsx`
```typescript
// test_renders_table_with_items
// test_sorts_columns_on_click
// test_displays_action_buttons
// test_handles_row_deletion
// test_shows_empty_state
// test_responsive_on_mobile
```

##### `test/unit/components/project-tasks/TaskBoardView.test.tsx`
```typescript
// test_renders_kanban_columns
// test_drag_and_drop_between_columns
// test_updates_task_status_on_drop
// test_displays_task_cards_correctly
// test_handles_empty_columns
// test_filters_tasks_by_assignee
```

##### `test/unit/components/project-tasks/BlockNoteEditor.test.tsx`
```typescript
// test_initializes_editor_with_content
// test_handles_content_changes
// test_serializes_content_to_json
// test_displays_toolbar_actions
// test_handles_keyboard_shortcuts
```

### 🟢 Standard Priority Tests (Week 2)

#### Unit Tests - Hooks

##### `test/unit/hooks/useNeonGlow.test.ts`
```typescript
// test_applies_glow_animation
// test_cleans_up_on_unmount
// test_calculates_style_values
// test_handles_animation_timing
```

##### `test/unit/hooks/useStaggeredEntrance.test.ts`
```typescript
// test_sequences_item_animations
// test_triggers_reanimation
// test_generates_animation_variants
// test_handles_empty_arrays
```

#### Unit Tests - Contexts

##### `test/unit/contexts/ToastContext.test.tsx`
```typescript
// test_shows_toast_messages
// test_queues_multiple_toasts
// test_auto_dismisses_toasts
// test_handles_toast_types
// test_provides_toast_methods
```

##### `test/unit/contexts/ThemeContext.test.tsx`
```typescript
// test_toggles_dark_light_mode
// test_persists_theme_preference
// test_detects_system_preference
// test_provides_theme_state
```

##### `test/unit/contexts/SettingsContext.test.tsx`
```typescript
// test_loads_settings_from_storage
// test_updates_settings_values
// test_persists_to_localstorage
// test_provides_settings_methods
```

#### Integration Tests - API

##### `test/integration/api/knowledge-api.test.ts`
```typescript
// test_knowledge_crud_operations
// test_file_upload_with_progress
// test_url_crawling_workflow
// test_search_functionality
// test_error_handling
```

##### `test/integration/api/project-api.test.ts`
```typescript
// test_project_crud_operations
// test_task_management_workflow
// test_real_time_updates
// test_status_transformations
```

### 🔵 Nice-to-Have Tests (Week 3)

#### Integration Tests - WebSockets

##### `test/integration/websockets/crawl-progress.test.ts`
```typescript
// test_connects_to_progress_stream
// test_receives_progress_updates
// test_handles_completion_events
// test_handles_error_events
// test_reconnects_on_disconnect
```

##### `test/integration/websockets/project-updates.test.ts`
```typescript
// test_receives_project_updates
// test_receives_task_updates
// test_handles_multiple_clients
// test_manages_subscriptions
```

#### E2E Tests - Workflows

##### `test/e2e/workflows/knowledge-workflow.test.ts`
```typescript
// test_complete_document_upload_flow
// test_url_crawling_and_search_flow
// test_knowledge_management_workflow
```

##### `test/e2e/workflows/project-workflow.test.ts`
```typescript
// test_create_project_with_tasks
// test_task_board_interactions
// test_document_versioning_flow
```

## Test Utilities and Configuration

### `test/setup.ts`
```typescript
// Global test setup
// DOM cleanup after each test
// Mock window.matchMedia
// Mock IntersectionObserver
// Configure test environment
```

### `test/fixtures/mocks/handlers.ts`
```typescript
// MSW handlers for all API endpoints
// WebSocket mock handlers
// File upload mock handlers
// Error response mocks
```

### `test/fixtures/test-utils.tsx`
```typescript
// Custom render with providers
// User event utilities
// Wait utilities
// Query utilities
// Mock component factories
```

### `test/fixtures/test-data.ts`
```typescript
// Sample knowledge items
// Sample projects and tasks
// Sample user data
// Sample API responses
// WebSocket message samples
```

## Coverage Goals

| Component Type | Target | Priority |
|----------------|--------|----------|
| Pages | 90% | Critical |
| Services | 95% | Critical |
| UI Components | 85% | High |
| Complex Components | 90% | High |
| Hooks | 95% | Medium |
| Contexts | 95% | Medium |
| Utils | 100% | Medium |
| E2E Flows | 80% | Low |

## Execution Order

1. **Week 1**: Page components + Critical services + WebSocket testing
2. **Week 2**: UI components + Complex components + API integration
3. **Week 3**: Remaining unit tests + E2E workflows

## Total Test Count

- **Unit Tests**: 127 test cases
- **Integration Tests**: 18 test cases
- **E2E Tests**: 6 test cases
- **Total**: 151 test cases

## Key Testing Focus Areas

### 1. **WebSocket Testing** (Critical)
- Connection management
- Reconnection logic
- Event handling
- Progress streaming
- Real-time updates

### 2. **User Interactions**
- Form submissions
- Drag and drop
- Modal interactions
- Toggle switches
- Search with debounce

### 3. **State Management**
- Context updates
- Local state sync
- Toast notifications
- Theme persistence

### 4. **Error Handling**
- API errors
- WebSocket failures
- Validation errors
- User feedback

### 5. **Accessibility**
- Keyboard navigation
- ARIA labels
- Screen reader support
- Focus management

This comprehensive test plan ensures full coverage of the Archon UI, with emphasis on critical user paths and real-time functionality.