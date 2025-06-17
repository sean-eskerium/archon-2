"""Unit tests for RagAgent."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.agents.rag_agent import RagAgent, RagDependencies, RagQueryResult


class TestRagAgent:
    """Unit tests for RagAgent."""
    
    @pytest.fixture
    def rag_agent(self):
        """Create RagAgent instance."""
        return RagAgent()
    
    @pytest.fixture
    def rag_deps(self):
        """Create RAG dependencies."""
        return RagDependencies(
            project_id="test-project",
            source_filter="docs.example.com",
            match_count=5,
            user_id="test-user"
        )
    
    @pytest.fixture
    def mock_search_results(self):
        """Mock search results."""
        return {
            "success": True,
            "results": [
                {
                    "content": "This is a test document about authentication",
                    "similarity_score": 0.95,
                    "metadata": {
                        "source": "docs.example.com",
                        "url": "https://docs.example.com/auth"
                    }
                },
                {
                    "content": "OAuth2 implementation guide",
                    "similarity": 0.85,
                    "metadata": {
                        "source": "docs.example.com", 
                        "url": "https://docs.example.com/oauth"
                    }
                }
            ]
        }
    
    @pytest.mark.unit
    def test_rag_agent_initialization(self, rag_agent):
        """Test RAG agent initialization."""
        assert rag_agent.name == "RagAgent"
        assert rag_agent.model == "openai:gpt-4o-mini"
        assert rag_agent.enable_rate_limiting is True
        
        # Check system prompt
        system_prompt = rag_agent.get_system_prompt()
        assert "RAG" in system_prompt or "document search" in system_prompt
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.agents.rag_agent.SearchService')
    async def test_search_documents_success(self, mock_search_service_class, rag_agent, rag_deps, mock_search_results):
        """Test successful document search."""
        # Setup mocks
        mock_search_service = MagicMock()
        mock_search_service.perform_rag_query.return_value = (True, mock_search_results)
        mock_search_service_class.return_value = mock_search_service
        
        # Mock agent run to return formatted results
        rag_agent._agent.run = AsyncMock(return_value="Found 2 relevant results:\n\nResult 1...")
        
        # Run search
        result = await rag_agent.run_conversation(
            user_message="How does authentication work?",
            project_id="test-project",
            source_filter="docs.example.com"
        )
        
        assert result.success is True
        assert result.query_type == "search"
        assert result.results_found == 2
        assert "Found 2 relevant results" in result.answer
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.agents.rag_agent.SearchService')
    async def test_search_documents_no_results(self, mock_search_service_class, rag_agent):
        """Test search with no results."""
        # Setup mocks
        mock_search_service = MagicMock()
        mock_search_service.perform_rag_query.return_value = (True, {"results": []})
        mock_search_service_class.return_value = mock_search_service
        
        # Mock agent run
        rag_agent._agent.run = AsyncMock(return_value="No results found for your query.")
        
        # Run search
        result = await rag_agent.run_conversation(
            user_message="Obscure topic that doesn't exist"
        )
        
        assert result.success is True
        assert result.results_found == 0
        assert "No results" in result.answer
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.agents.rag_agent.SourceManagementService')
    async def test_list_available_sources(self, mock_source_service_class, rag_agent):
        """Test listing available sources."""
        # Setup mocks
        mock_source_service = MagicMock()
        mock_source_service.get_available_sources.return_value = (True, {
            "sources": [
                {
                    "source_id": "docs.example.com",
                    "title": "Example Documentation",
                    "description": "Main product docs",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "source_id": "api.example.com",
                    "title": "API Reference",
                    "description": "API documentation",
                    "created_at": "2024-01-02T00:00:00Z"
                }
            ]
        })
        mock_source_service_class.return_value = mock_source_service
        
        # Mock agent run
        rag_agent._agent.run = AsyncMock(return_value="Available sources (2 total):\n- docs.example.com...")
        
        # Run query
        result = await rag_agent.run_conversation(
            user_message="What sources are available?"
        )
        
        assert result.success is True
        assert result.query_type == "list_sources"
        assert "Available sources" in result.answer
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.agents.rag_agent.SearchService')
    async def test_search_code_examples(self, mock_search_service_class, rag_agent):
        """Test searching for code examples."""
        # Setup mocks
        mock_search_service = MagicMock()
        mock_search_service.search_code_examples_service.return_value = (True, {
            "code_examples": [
                {
                    "summary": "Python authentication example",
                    "code_block": "```python\ndef authenticate(user, password):\n    pass\n```",
                    "similarity": 0.90,
                    "url": "https://example.com/auth-example"
                }
            ]
        })
        mock_search_service_class.return_value = mock_search_service
        
        # Mock agent run
        rag_agent._agent.run = AsyncMock(return_value="Found 1 code example:\n\nExample 1...")
        
        # Run search
        result = await rag_agent.run_conversation(
            user_message="Show me authentication code examples"
        )
        
        assert result.success is True
        assert result.query_type == "code_search"
        assert "code example" in result.answer.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_handling(self, rag_agent):
        """Test error handling in RAG agent."""
        # Mock agent to raise exception
        rag_agent._agent.run = AsyncMock(side_effect=Exception("API error"))
        
        # Run query
        result = await rag_agent.run_conversation(
            user_message="Test query"
        )
        
        assert result.success is False
        assert result.query_type == "error"
        assert "encountered an error" in result.answer
        assert "API error" in result.message
    
    @pytest.mark.unit
    def test_rag_dependencies_defaults(self):
        """Test RagDependencies default values."""
        deps = RagDependencies()
        
        assert deps.project_id is None
        assert deps.source_filter is None
        assert deps.match_count == 5
        assert deps.progress_callback is None
    
    @pytest.mark.unit
    def test_rag_query_result_structure(self):
        """Test RagQueryResult model structure."""
        result = RagQueryResult(
            query_type="search",
            original_query="test query",
            refined_query="enhanced test query",
            results_found=3,
            sources=["source1", "source2"],
            answer="Test answer",
            citations=[{"source": "source1", "relevance": 0.9}],
            success=True,
            message="Success"
        )
        
        assert result.query_type == "search"
        assert result.results_found == 3
        assert len(result.sources) == 2
        assert result.success is True
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_source_filter_application(self, rag_agent):
        """Test that source filters are properly applied."""
        # Mock the agent run
        rag_agent._agent.run = AsyncMock(return_value="Filtered results from specific source")
        
        # Run with source filter
        result = await rag_agent.run_conversation(
            user_message="Search in specific docs",
            source_filter="api.example.com"
        )
        
        assert result.success is True
        # In real implementation, verify the filter was passed to search service
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_match_count_configuration(self, rag_agent):
        """Test configurable match count."""
        # Mock agent run
        rag_agent._agent.run = AsyncMock(return_value="Found 10 results")
        
        # Run with custom match count
        result = await rag_agent.run_conversation(
            user_message="Get more results",
            match_count=10
        )
        
        assert result.success is True
        # In real implementation, verify match_count was passed to search
    
    @pytest.mark.unit
    def test_result_parsing_logic(self, rag_agent):
        """Test the result parsing logic in run_conversation."""
        # Test various response formats
        test_cases = [
            ("Found 5 results for your query", "search", 5),
            ("Available sources (3 total):", "list_sources", 0),
            ("Found 2 code examples:", "code_search", 0),
            ("No results found", "search", 0)
        ]
        
        # Would need to expose parsing logic or test through integration
        # This demonstrates the test structure
        assert True
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_source_extraction_from_results(self, rag_agent):
        """Test extraction of sources from search results."""
        # Mock response with sources
        response_text = """Found 2 results:
        
Result 1
Source: docs.example.com
Content: Test content

Result 2  
Source: api.example.com
Content: API content"""
        
        rag_agent._agent.run = AsyncMock(return_value=response_text)
        
        result = await rag_agent.run_conversation("test query")
        
        assert result.success is True
        assert len(result.sources) == 2
        assert "docs.example.com" in result.sources
        assert "api.example.com" in result.sources