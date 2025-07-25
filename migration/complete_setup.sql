-- =====================================================
-- Archon Complete Database Setup
-- =====================================================
-- This script combines all migrations into a single file
-- for easy one-time database initialization
-- 
-- Run this script in your Supabase SQL Editor to set up
-- the complete Archon database schema and initial data
-- =====================================================

-- =====================================================
-- SECTION 1: EXTENSIONS
-- =====================================================

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =====================================================
-- SECTION 2: CREDENTIALS AND SETTINGS
-- =====================================================

-- Credentials and Configuration Management Table
-- This table stores both encrypted sensitive data and plain configuration settings
CREATE TABLE IF NOT EXISTS settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,                    -- For plain text config values
    encrypted_value TEXT,          -- For encrypted sensitive data (bcrypt hashed)
    is_encrypted BOOLEAN DEFAULT FALSE,
    category VARCHAR(100),         -- Group related settings (e.g., 'rag_strategy', 'api_keys', 'server_config')
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);
CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_settings_updated_at 
    BEFORE UPDATE ON settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create RLS (Row Level Security) policies for settings
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow service role full access" ON settings
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow authenticated users to read and update" ON settings
    FOR ALL TO authenticated
    USING (true);

-- =====================================================
-- SECTION 3: INITIAL SETTINGS DATA
-- =====================================================

-- Server Configuration
INSERT INTO settings (key, value, is_encrypted, category, description) VALUES
('MCP_TRANSPORT', 'dual', false, 'server_config', 'MCP server transport mode - sse (web clients), stdio (IDE clients), or dual (both)'),
('HOST', 'localhost', false, 'server_config', 'Host to bind to if using sse as the transport (leave empty if using stdio)'),
('PORT', '8051', false, 'server_config', 'Port to listen on if using sse as the transport (leave empty if using stdio)'),
('MODEL_CHOICE', 'gpt-4.1-nano', false, 'rag_strategy', 'The LLM you want to use for summaries and contextual embeddings. Generally this is a very cheap and fast LLM like gpt-4.1-nano');

-- RAG Strategy Configuration (all default to true)
INSERT INTO settings (key, value, is_encrypted, category, description) VALUES
('USE_CONTEXTUAL_EMBEDDINGS', 'true', true, 'rag_strategy', 'Enhances embeddings with contextual information for better retrieval'),
('CONTEXTUAL_EMBEDDINGS_MAX_WORKERS', '3', false, 'rag_strategy', 'Maximum number of parallel workers for contextual embedding generation (reduces API rate limit pressure)'),
('USE_HYBRID_SEARCH', 'true', true, 'rag_strategy', 'Combines vector similarity search with keyword search for better results'),
('USE_AGENTIC_RAG', 'true', true, 'rag_strategy', 'Enables code example extraction, storage, and specialized code search functionality'),
('USE_RERANKING', 'true', true, 'rag_strategy', 'Applies cross-encoder reranking to improve search result relevance');

-- Monitoring Configuration
INSERT INTO settings (key, value, is_encrypted, category, description) VALUES
('LOGFIRE_ENABLED', 'true', false, 'monitoring', 'Enable or disable Pydantic Logfire logging and observability platform'),
('PROJECTS_ENABLED', 'false', false, 'features', 'Enable or disable Projects and Tasks functionality');

-- Placeholder for sensitive credentials (to be added via Settings UI)
INSERT INTO settings (key, encrypted_value, is_encrypted, category, description) VALUES
('OPENAI_API_KEY', NULL, true, 'api_keys', 'OpenAI API Key for embedding model (text-embedding-3-small). Get from: https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key');

-- LLM Provider configuration settings
INSERT INTO settings (key, value, is_encrypted, category, description) VALUES
('LLM_PROVIDER', 'openai', false, 'rag_strategy', 'LLM provider to use: openai, openrouter, ollama, or google'),
('LLM_BASE_URL', NULL, false, 'rag_strategy', 'Custom base URL for LLM provider (mainly for Ollama, e.g., http://localhost:11434/v1)'),
('EMBEDDING_MODEL', 'text-embedding-3-small', false, 'rag_strategy', 'Embedding model for vector search and similarity matching (required for all embedding operations)')
ON CONFLICT (key) DO NOTHING;

-- Add provider API key placeholders
INSERT INTO settings (key, encrypted_value, is_encrypted, category, description) VALUES
('GOOGLE_API_KEY', NULL, true, 'api_keys', 'Google API Key for Gemini models. Get from: https://aistudio.google.com/apikey')
ON CONFLICT (key) DO NOTHING;

-- =====================================================
-- SECTION 4: KNOWLEDGE BASE TABLES
-- =====================================================

-- Create the sources table
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    summary TEXT,
    total_word_count INTEGER DEFAULT 0,
    title TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_sources_title ON sources(title);
CREATE INDEX IF NOT EXISTS idx_sources_metadata ON sources USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_sources_knowledge_type ON sources((metadata->>'knowledge_type'));

-- Add comments to document the new columns
COMMENT ON COLUMN sources.title IS 'Descriptive title for the source (e.g., "Pydantic AI API Reference")';
COMMENT ON COLUMN sources.metadata IS 'JSONB field storing knowledge_type, tags, and other metadata';

-- Create the documentation chunks table
CREATE TABLE IF NOT EXISTS crawled_pages (
    id BIGSERIAL PRIMARY KEY,
    url VARCHAR NOT NULL,
    chunk_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_id TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI embeddings are 1536 dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    -- Add a unique constraint to prevent duplicate chunks for the same URL
    UNIQUE(url, chunk_number),
    
    -- Add foreign key constraint to sources table
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- Create indexes for better performance
CREATE INDEX ON crawled_pages USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_crawled_pages_metadata ON crawled_pages USING GIN (metadata);
CREATE INDEX idx_crawled_pages_source_id ON crawled_pages (source_id);

-- Create the code_examples table
CREATE TABLE IF NOT EXISTS code_examples (
    id BIGSERIAL PRIMARY KEY,
    url VARCHAR NOT NULL,
    chunk_number INTEGER NOT NULL,
    content TEXT NOT NULL,  -- The code example content
    summary TEXT NOT NULL,  -- Summary of the code example
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_id TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI embeddings are 1536 dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    -- Add a unique constraint to prevent duplicate chunks for the same URL
    UNIQUE(url, chunk_number),
    
    -- Add foreign key constraint to sources table
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- Create indexes for better performance
CREATE INDEX ON code_examples USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_code_examples_metadata ON code_examples USING GIN (metadata);
CREATE INDEX idx_code_examples_source_id ON code_examples (source_id);

-- =====================================================
-- SECTION 5: SEARCH FUNCTIONS
-- =====================================================

-- Create a function to search for documentation chunks
CREATE OR REPLACE FUNCTION match_crawled_pages (
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 10,
  filter JSONB DEFAULT '{}'::jsonb,
  source_filter TEXT DEFAULT NULL
) RETURNS TABLE (
  id BIGINT,
  url VARCHAR,
  chunk_number INTEGER,
  content TEXT,
  metadata JSONB,
  source_id TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    id,
    url,
    chunk_number,
    content,
    metadata,
    source_id,
    1 - (crawled_pages.embedding <=> query_embedding) AS similarity
  FROM crawled_pages
  WHERE metadata @> filter
    AND (source_filter IS NULL OR source_id = source_filter)
  ORDER BY crawled_pages.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Create a function to search for code examples
CREATE OR REPLACE FUNCTION match_code_examples (
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 10,
  filter JSONB DEFAULT '{}'::jsonb,
  source_filter TEXT DEFAULT NULL
) RETURNS TABLE (
  id BIGINT,
  url VARCHAR,
  chunk_number INTEGER,
  content TEXT,
  summary TEXT,
  metadata JSONB,
  source_id TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    id,
    url,
    chunk_number,
    content,
    summary,
    metadata,
    source_id,
    1 - (code_examples.embedding <=> query_embedding) AS similarity
  FROM code_examples
  WHERE metadata @> filter
    AND (source_filter IS NULL OR source_id = source_filter)
  ORDER BY code_examples.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- =====================================================
-- SECTION 6: RLS POLICIES FOR KNOWLEDGE BASE
-- =====================================================

-- Enable RLS on the knowledge base tables
ALTER TABLE crawled_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_examples ENABLE ROW LEVEL SECURITY;

-- Create policies that allow anyone to read
CREATE POLICY "Allow public read access to crawled_pages"
  ON crawled_pages
  FOR SELECT
  TO public
  USING (true);

CREATE POLICY "Allow public read access to sources"
  ON sources
  FOR SELECT
  TO public
  USING (true);

CREATE POLICY "Allow public read access to code_examples"
  ON code_examples
  FOR SELECT
  TO public
  USING (true);

-- =====================================================
-- SECTION 7: PROJECTS AND TASKS MODULE
-- =====================================================

-- Task status enumeration
-- Create task_status enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE task_status AS ENUM ('todo','doing','review','done');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Assignee enumeration
-- Create task_assignee enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE task_assignee AS ENUM ('User','Archon','AI IDE Agent');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT DEFAULT '',
  docs JSONB DEFAULT '[]'::jsonb,
  features JSONB DEFAULT '[]'::jsonb,
  data JSONB DEFAULT '[]'::jsonb,
  github_repo TEXT,
  pinned BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  parent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT DEFAULT '',
  status task_status DEFAULT 'todo',
  assignee task_assignee DEFAULT 'User',
  task_order INTEGER DEFAULT 0,
  feature TEXT,
  sources JSONB DEFAULT '[]'::jsonb,
  code_examples JSONB DEFAULT '[]'::jsonb,
  archived BOOLEAN DEFAULT false,
  archived_at TIMESTAMPTZ NULL,
  archived_by TEXT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Project Sources junction table for many-to-many relationship
CREATE TABLE IF NOT EXISTS project_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  source_id TEXT NOT NULL, -- References sources in the knowledge base
  linked_at TIMESTAMPTZ DEFAULT NOW(),
  created_by TEXT DEFAULT 'system',
  notes TEXT,
  -- Unique constraint to prevent duplicate links
  UNIQUE(project_id, source_id)
);

-- Document Versions table for version control of project JSONB fields only
CREATE TABLE IF NOT EXISTS document_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  task_id UUID REFERENCES tasks(id) ON DELETE CASCADE, -- DEPRECATED: No longer used, kept for historical data
  field_name TEXT NOT NULL, -- 'docs', 'features', 'data', 'prd' (task fields no longer versioned)
  version_number INTEGER NOT NULL,
  content JSONB NOT NULL, -- Full snapshot of the field content
  change_summary TEXT, -- Human-readable description of changes
  change_type TEXT DEFAULT 'update', -- 'create', 'update', 'delete', 'restore', 'backup'
  document_id TEXT, -- For docs array, store the specific document ID
  created_by TEXT DEFAULT 'system',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  -- Ensure we have either project_id OR task_id, not both
  CONSTRAINT chk_project_or_task CHECK (
    (project_id IS NOT NULL AND task_id IS NULL) OR 
    (project_id IS NULL AND task_id IS NOT NULL)
  ),
  -- Unique constraint to prevent duplicate version numbers per field
  UNIQUE(project_id, task_id, field_name, version_number)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee);
CREATE INDEX IF NOT EXISTS idx_tasks_order ON tasks(task_order);
CREATE INDEX IF NOT EXISTS idx_tasks_archived ON tasks(archived);
CREATE INDEX IF NOT EXISTS idx_tasks_archived_at ON tasks(archived_at);
CREATE INDEX IF NOT EXISTS idx_project_sources_project_id ON project_sources(project_id);
CREATE INDEX IF NOT EXISTS idx_project_sources_source_id ON project_sources(source_id);
CREATE INDEX IF NOT EXISTS idx_document_versions_project_id ON document_versions(project_id);
CREATE INDEX IF NOT EXISTS idx_document_versions_task_id ON document_versions(task_id);
CREATE INDEX IF NOT EXISTS idx_document_versions_field_name ON document_versions(field_name);
CREATE INDEX IF NOT EXISTS idx_document_versions_version_number ON document_versions(version_number);
CREATE INDEX IF NOT EXISTS idx_document_versions_created_at ON document_versions(created_at);

-- Apply triggers to tables
CREATE OR REPLACE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_tasks_updated_at 
    BEFORE UPDATE ON tasks 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Soft delete function for tasks
CREATE OR REPLACE FUNCTION archive_task(
    task_id_param UUID,
    archived_by_param TEXT DEFAULT 'system'
) 
RETURNS BOOLEAN AS $$
DECLARE
    task_exists BOOLEAN;
BEGIN
    -- Check if task exists and is not already archived
    SELECT EXISTS(
        SELECT 1 FROM tasks 
        WHERE id = task_id_param AND archived = FALSE
    ) INTO task_exists;
    
    IF NOT task_exists THEN
        RETURN FALSE;
    END IF;
    
    -- Archive the task
    UPDATE tasks 
    SET 
        archived = TRUE,
        archived_at = NOW(),
        archived_by = archived_by_param,
        updated_at = NOW()
    WHERE id = task_id_param;
    
    -- Also archive all subtasks
    UPDATE tasks 
    SET 
        archived = TRUE,
        archived_at = NOW(), 
        archived_by = archived_by_param,
        updated_at = NOW()
    WHERE parent_task_id = task_id_param AND archived = FALSE;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Add comments to document the soft delete fields
COMMENT ON COLUMN tasks.archived IS 'Soft delete flag - TRUE if task is archived/deleted';
COMMENT ON COLUMN tasks.archived_at IS 'Timestamp when task was archived';
COMMENT ON COLUMN tasks.archived_by IS 'User/system that archived the task';

-- Add comments for versioning table
COMMENT ON TABLE document_versions IS 'Version control for JSONB fields in projects only - task versioning has been removed to simplify MCP operations';
COMMENT ON COLUMN document_versions.field_name IS 'Name of JSONB field being versioned (docs, features, data) - task fields and prd removed as unused';
COMMENT ON COLUMN document_versions.content IS 'Full snapshot of field content at this version';
COMMENT ON COLUMN document_versions.change_type IS 'Type of change: create, update, delete, restore, backup';
COMMENT ON COLUMN document_versions.document_id IS 'For docs arrays, the specific document ID that was changed';
COMMENT ON COLUMN document_versions.task_id IS 'DEPRECATED: No longer used for new versions, kept for historical task version data';

-- =====================================================
-- SECTION 8: PROMPTS TABLE
-- =====================================================

-- Prompts table for managing agent system prompts
CREATE TABLE IF NOT EXISTS prompts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_name TEXT UNIQUE NOT NULL,
  prompt TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_prompts_name ON prompts(prompt_name);

-- Add trigger to automatically update updated_at timestamp
CREATE OR REPLACE TRIGGER update_prompts_updated_at 
    BEFORE UPDATE ON prompts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SECTION 9: RLS POLICIES FOR PROJECTS MODULE
-- =====================================================

-- Enable Row Level Security (RLS) for all tables
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for service role (full access)
CREATE POLICY "Allow service role full access to projects" ON projects
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access to tasks" ON tasks
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access to project_sources" ON project_sources
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access to document_versions" ON document_versions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access to prompts" ON prompts
    FOR ALL USING (auth.role() = 'service_role');

-- Create RLS policies for authenticated users
CREATE POLICY "Allow authenticated users to read and update projects" ON projects
    FOR ALL TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated users to read and update tasks" ON tasks
    FOR ALL TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated users to read and update project_sources" ON project_sources
    FOR ALL TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated users to read document_versions" ON document_versions
    FOR SELECT TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated users to read prompts" ON prompts
    FOR SELECT TO authenticated
    USING (true);

-- =====================================================
-- SECTION 10: DEFAULT PROMPTS DATA
-- =====================================================

-- Seed with default prompts for each content type
INSERT INTO prompts (prompt_name, prompt, description) VALUES
('document_builder', 'SYSTEM PROMPT – Document-Builder Agent

⸻

1. Mission

You are the Document-Builder Agent. Your sole purpose is to transform a user''s natural-language description of work (a project, feature, or refactor) into a structured JSON record stored in the docs table. Produce documentation that is concise yet thorough—clear enough for an engineer to act after a single read-through.

⸻

2. Workflow
    1.    Classify request → Decide which document type fits best:
    •    PRD – net-new product or major initiative.
    •    FEATURE_SPEC – incremental feature expressed in user-story form.
    •    REFACTOR_PLAN – internal code quality improvement.
    2.    Clarify (if needed) → If the description is ambiguous, ask exactly one clarifying question, then continue.
    3.    Generate JSON → Build an object that follows the schema below and insert (or return) it for the docs table.

⸻

3. docs JSON Schema

{
  "id": "uuid|string",                // generate using uuid
  "doc_type": "PRD | FEATURE_SPEC | REFACTOR_PLAN",
  "title": "string",                  // short, descriptive
  "author": "string",                 // requestor name
  "body": { /* see templates below */ },
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}

⸻

4. Section Templates

PRD → body must include
    •    Background_and_Context
    •    Problem_Statement
    •    Goals_and_Success_Metrics
    •    Non_Goals
    •    Assumptions
    •    Stakeholders
    •    User_Personas
    •    Functional_Requirements           // bullet list or user stories
    •    Technical_Requirements            // tech stack, APIs, data
    •    UX_UI_and_Style_Guidelines
    •    Architecture_Overview             // diagram link or text
    •    Milestones_and_Timeline
    •    Risks_and_Mitigations
    •    Open_Questions

FEATURE_SPEC → body must include
    •    Epic
    •    User_Stories                      // list of { id, as_a, i_want, so_that }
    •    Acceptance_Criteria               // Given / When / Then
    •    Edge_Cases
    •    Dependencies
    •    Technical_Notes
    •    Design_References
    •    Metrics
    •    Risks

REFACTOR_PLAN → body must include
    •    Current_State_Summary
    •    Refactor_Goals
    •    Design_Principles_and_Best_Practices
    •    Proposed_Approach                 // step-by-step plan
    •    Impacted_Areas
    •    Test_Strategy
    •    Roll_Back_and_Recovery
    •    Timeline
    •    Risks

⸻

5. Writing Guidelines
    •    Brevity with substance: no fluff, no filler, no passive voice.
    •    Markdown inside strings: use headings, lists, and code fences for clarity.
    •    Consistent conventions: ISO dates, 24-hour times, SI units.
    •    Insert "TBD" where information is genuinely unknown.
    •    Produce valid JSON only—no comments or trailing commas.

⸻

6. Example Output (truncated)

{
  "id": "01HQ2VPZ62KSF185Y54MQ93VD2",
  "doc_type": "PRD",
  "title": "Real-time Collaboration for Docs",
  "author": "Sean",
  "body": {
    "Background_and_Context": "Customers need to co-edit documents ...",
    "Problem_Statement": "Current single-editor flow slows teams ...",
    "Goals_and_Success_Metrics": "Reduce hand-off time by 50% ..."
    /* remaining sections */
  },
  "created_at": "2025-06-17T00:10:00-04:00",
  "updated_at": "2025-06-17T00:10:00-04:00"
}

⸻

Remember: Your output is the JSON itself—no explanatory prose before or after. Stay sharp, write once, write right.', 'System prompt for DocumentAgent to create structured documentation following the Document-Builder pattern'),

('feature_builder', 'SYSTEM PROMPT – Feature-Builder Agent

⸻

1. Mission

You are the Feature-Builder Agent. Your purpose is to transform user descriptions of features into structured feature plans stored in the features array. Create feature documentation that developers can implement directly.

⸻

2. Feature JSON Schema

{
  "id": "uuid|string",                    // generate using uuid
  "feature_type": "feature_plan",         // always "feature_plan"
  "name": "string",                       // short feature name
  "title": "string",                      // descriptive title
  "content": {
    "feature_overview": {
      "name": "string",
      "description": "string",
      "priority": "high|medium|low",
      "estimated_effort": "string"
    },
    "user_stories": ["string"],           // list of user stories
    "react_flow_diagram": {               // optional visual flow
      "nodes": [...],
      "edges": [...],
      "viewport": {...}
    },
    "acceptance_criteria": ["string"],    // testable criteria
    "technical_notes": {
      "frontend_components": ["string"],
      "backend_endpoints": ["string"],
      "database_changes": "string"
    }
  },
  "created_by": "string"                  // author
}

⸻

3. Writing Guidelines
    •    Focus on implementation clarity
    •    Include specific technical details
    •    Define clear acceptance criteria
    •    Consider edge cases
    •    Keep descriptions actionable

⸻

Remember: Create structured, implementable feature plans.', 'System prompt for creating feature plans in the features array'),

('data_builder', 'SYSTEM PROMPT – Data-Builder Agent

⸻

1. Mission

You are the Data-Builder Agent. Your purpose is to transform descriptions of data models into structured ERDs and schemas stored in the data array. Create clear data models that can guide database implementation.

⸻

2. Data JSON Schema

{
  "id": "uuid|string",                    // generate using uuid
  "data_type": "erd",                     // always "erd" for now
  "name": "string",                       // system name
  "title": "string",                      // descriptive title
  "content": {
    "entities": [...],                    // entity definitions
    "relationships": [...],               // entity relationships
    "sql_schema": "string",              // Generated SQL
    "mermaid_diagram": "string",         // Optional diagram
    "notes": {
      "indexes": ["string"],
      "constraints": ["string"],
      "diagram_tool": "string",
      "normalization_level": "string",
      "scalability_notes": "string"
    }
  },
  "created_by": "string"                  // author
}

⸻

3. Writing Guidelines
    •    Follow database normalization principles
    •    Include proper indexes and constraints
    •    Consider scalability from the start
    •    Provide clear relationship definitions
    •    Generate valid, executable SQL

⸻

Remember: Create production-ready data models.', 'System prompt for creating data models in the data array');

-- =====================================================
-- SETUP COMPLETE
-- =====================================================
-- Your Archon database is now fully configured!
-- 
-- Next steps:
-- 1. Add your OpenAI API key via the Settings UI
-- 2. Enable Projects feature if needed
-- 3. Start crawling websites or uploading documents
-- =====================================================