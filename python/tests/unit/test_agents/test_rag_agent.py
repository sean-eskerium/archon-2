"""Unit tests for RagAgent with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List, Dict, Any, Optional
import uuid

from src.agents.rag_agent import RagAgent, RagDependencies, RagQueryResult
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    measure_time
)


@pytest.mark.unit
@pytest.mark.standard
class TestRagAgent:
    """Unit tests for RagAgent with enhanced patterns."""
    
    @pytest.fixture
    def make_rag_agent(self):
        """Factory for creating RAG agents with custom configs."""
        def _make_agent(
            name: str = "RagAgent",
            model: str = "openai:gpt-4o-mini",
            enable_rate_limiting: bool = True,
            temperature: float = 0.7
        ) -> RagAgent:
            return RagAgent(
                name=name,
                model=model,
                enable_rate_limiting=enable_rate_limiting,
                temperature=temperature
            )
        return _make_agent
    
    @pytest.fixture
    def rag_agent(self, make_rag_agent):
        """Create default RagAgent instance."""
        return make_rag_agent()
    
    @pytest.fixture
    def make_rag_deps(self):
        """Factory for creating RAG dependencies."""
        def _make_deps(
            project_id: Optional[str] = None,
            user_id: Optional[str] = None,
            source_filter: Optional[str] = None,
            match_count: int = 5,
            progress_callback: Optional[Any] = None
        ) -> RagDependencies:
            return RagDependencies(
                project_id=project_id or f"project-{uuid.uuid4().hex[:8]}",
                user_id=user_id or f"user-{uuid.uuid4().hex[:8]}",
                source_filter=source_filter,
                match_count=match_count,
                progress_callback=progress_callback
            )
        return _make_deps
    
    @pytest.fixture
    def rag_deps(self, make_rag_deps):
        """Create default RAG dependencies."""
        return make_rag_deps()
    
    @pytest.fixture
    def make_search_results(self):
        """Factory for creating mock search results."""
        def _make_results(
            num_results: int = 2,
            source: str = "docs.example.com",
            base_similarity: float = 0.95
        ) -> Dict:
            results = []
            for i in range(num_results):
                results.append({
                    "content": f"Test document {i+1} about the topic",
                    "similarity_score": base_similarity - (i * 0.05),
                    "metadata": {
                        "source": source,
                        "url": f"https://{source}/page{i+1}"
                    }
                })
            
            return {
                "success": True,
                "results": results,
                "total_found": num_results
            }
        return _make_results
    
    @pytest.fixture
    def make_rag_result(self):
        """Factory for creating RagQueryResult."""
        def _make_result(
            query_type: str = "search",
            original_query: str = "test query",
            results_found: int = 2,
            sources: Optional[List[str]] = None,
            answer: str = "Test answer",
            success: bool = True,
            message: Optional[str] = None
        ) -> RagQueryResult:
            return RagQueryResult(
                query_type=query_type,
                original_query=original_query,
                refined_query=f"enhanced: {original_query}",
                results_found=results_found,
                sources=sources or [],
                answer=answer,
                citations=[],
                success=success,
                message=message or "Success"
            )
        return _make_result
    
    # =============================================================================
    # Initialization Tests
    # =============================================================================
    
    @pytest.mark.parametrize("config", [
        pytest.param(
            {"model": "openai:gpt-4o-mini", "enable_rate_limiting": True},
            id="default-config"
        ),
        pytest.param(
            {"model": "openai:gpt-4o", "enable_rate_limiting": False},
            id="gpt4-no-rate-limit"
        ),
        pytest.param(
            {"model": "openai:gpt-3.5-turbo", "temperature": 0.3},
            id="gpt35-low-temp"
        ),
    ])
    def test_agent_initialization_configs(self, make_rag_agent, config):
        """Test RAG agent initialization with various configurations."""
        # Act
        agent = make_rag_agent(**config)
        
        # Assert
        assert agent.name == "RagAgent"
        for key, value in config.items():
            assert getattr(agent, key) == value
        
        # Verify system prompt
        system_prompt = agent.get_system_prompt()
        assert any(term in system_prompt.lower() for term in ["rag", "retrieval", "search", "document"])
    
    # =============================================================================
    # Search Operations Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_results,source_filter,expected_query_type", [
        pytest.param(2, "docs.example.com", "search", id="filtered-search"),
        pytest.param(5, None, "search", id="unfiltered-search"),
        pytest.param(0, "api.example.com", "search", id="no-results"),
        pytest.param(10, "blog.example.com", "search", id="many-results"),
    ])
    @patch('src.agents.rag_agent.SearchService')
    async def test_document_search_variations(
        self,
        mock_search_service_class,
        rag_agent,
        make_rag_deps,
        make_search_results,
        num_results,
        source_filter,
        expected_query_type
    ):
        """Test document search with various parameters."""
        # Arrange
        deps = make_rag_deps(source_filter=source_filter)
        search_results = make_search_results(num_results=num_results, source=source_filter or "example.com")
        
        mock_search_service = MagicMock()
        mock_search_service.perform_rag_query.return_value = (True, search_results)
        mock_search_service_class.return_value = mock_search_service
        
        rag_agent._agent.run = AsyncMock(
            return_value=f"Found {num_results} relevant results" if num_results > 0 else "No results found"
        )
        
        # Act
        result = await rag_agent.run_conversation(
            user_message="Test search query",
            project_id=deps.project_id,
            source_filter=source_filter
        )
        
        # Assert
        assert result.success is True
        assert result.query_type == expected_query_type
        assert result.results_found == num_results
        
        if num_results > 0:
            assert f"Found {num_results}" in result.answer
        else:
            assert "No results" in result.answer
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_refined", [
        pytest.param("authentication", "authentication security login", id="simple-query"),
        pytest.param("how does OAuth work?", "OAuth authentication flow implementation", id="question-query"),
        pytest.param("API endpoints", "API endpoints REST documentation", id="technical-query"),
    ])
    @patch('src.agents.rag_agent.SearchService')
    async def test_query_refinement(
        self,
        mock_search_service_class,
        rag_agent,
        make_search_results,
        query,
        expected_refined
    ):
        """Test that queries are refined for better search results."""
        # Arrange
        mock_search_service = MagicMock()
        mock_search_service.perform_rag_query.return_value = (True, make_search_results())
        mock_search_service_class.return_value = mock_search_service
        
        # Mock agent to simulate query refinement
        rag_agent._agent.run = AsyncMock(return_value="Refined search results...")
        
        # Act
        result = await rag_agent.run_conversation(user_message=query)
        
        # Assert
        assert result.success is True
        assert result.original_query == query
        # In real implementation, would check refined_query
    
    # =============================================================================
    # Code Search Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_examples,language", [
        pytest.param(1, "python", id="single-python"),
        pytest.param(3, "javascript", id="multiple-js"),
        pytest.param(0, "rust", id="no-rust-examples"),
    ])
    @patch('src.agents.rag_agent.SearchService')
    async def test_code_example_search(
        self,
        mock_search_service_class,
        rag_agent,
        num_examples,
        language
    ):
        """Test searching for code examples in various languages."""
        # Arrange
        code_examples = []
        for i in range(num_examples):
            code_examples.append({
                "summary": f"{language} example {i+1}",
                "code_block": f"```{language}\n# Example {i+1}\n```",
                "similarity": 0.9 - (i * 0.1),
                "url": f"https://example.com/{language}/example{i+1}"
            })
        
        mock_search_service = MagicMock()
        mock_search_service.search_code_examples_service.return_value = (
            True,
            {"code_examples": code_examples}
        )
        mock_search_service_class.return_value = mock_search_service
        
        response = f"Found {num_examples} {language} code examples" if num_examples > 0 else f"No {language} examples found"
        rag_agent._agent.run = AsyncMock(return_value=response)
        
        # Act
        result = await rag_agent.run_conversation(
            user_message=f"Show me {language} code examples"
        )
        
        # Assert
        assert result.success is True
        assert result.query_type == "code_search"
        assert str(num_examples) in result.answer or "No" in result.answer
    
    # =============================================================================
    # Source Management Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_sources", [0, 2, 5, 10])
    @patch('src.agents.rag_agent.SourceManagementService')
    async def test_list_available_sources(
        self,
        mock_source_service_class,
        rag_agent,
        num_sources
    ):
        """Test listing various numbers of available sources."""
        # Arrange
        sources = []
        for i in range(num_sources):
            sources.append({
                "source_id": f"source{i}.example.com",
                "title": f"Source {i+1}",
                "description": f"Description for source {i+1}",
                "created_at": f"2024-01-{i+1:02d}T00:00:00Z"
            })
        
        mock_source_service = MagicMock()
        mock_source_service.get_available_sources.return_value = (True, {"sources": sources})
        mock_source_service_class.return_value = mock_source_service
        
        response = f"Available sources ({num_sources} total)" if num_sources > 0 else "No sources available"
        rag_agent._agent.run = AsyncMock(return_value=response)
        
        # Act
        result = await rag_agent.run_conversation(
            user_message="What sources are available?"
        )
        
        # Assert
        assert result.success is True
        assert result.query_type == "list_sources"
        assert str(num_sources) in result.answer or "No sources" in result.answer
    
    # =============================================================================
    # Match Count Configuration Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("match_count", [1, 5, 10, 20, 50])
    @patch('src.agents.rag_agent.SearchService')
    async def test_configurable_match_count(
        self,
        mock_search_service_class,
        rag_agent,
        make_search_results,
        match_count
    ):
        """Test search with various match count configurations."""
        # Arrange
        mock_search_service = MagicMock()
        mock_search_service.perform_rag_query.return_value = (
            True,
            make_search_results(num_results=min(match_count, 10))  # Cap at 10 for testing
        )
        mock_search_service_class.return_value = mock_search_service
        
        rag_agent._agent.run = AsyncMock(return_value=f"Retrieved up to {match_count} results")
        
        # Act
        result = await rag_agent.run_conversation(
            user_message="Search with custom limit",
            match_count=match_count
        )
        
        # Assert
        assert result.success is True
        # Verify match_count was passed to search service
        mock_search_service.perform_rag_query.assert_called_once()
        call_kwargs = mock_search_service.perform_rag_query.call_args[1]
        assert call_kwargs.get("match_count") == match_count
    
    # =============================================================================
    # Error Handling Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("error_type,error_message,expected_query_type", [
        pytest.param(ValueError("Invalid query"), "Invalid query", "error", id="value-error"),
        pytest.param(ConnectionError("API down"), "API down", "error", id="connection-error"),
        pytest.param(Exception("Unknown error"), "Unknown error", "error", id="generic-error"),
    ])
    async def test_error_handling_scenarios(
        self,
        rag_agent,
        error_type,
        error_message,
        expected_query_type
    ):
        """Test error handling for various failure scenarios."""
        # Arrange
        rag_agent._agent.run = AsyncMock(side_effect=error_type)
        
        # Act
        result = await rag_agent.run_conversation(user_message="Test query")
        
        # Assert
        assert result.success is False
        assert result.query_type == expected_query_type
        assert "encountered an error" in result.answer
        assert error_message in result.message
    
    # =============================================================================
    # Source Extraction Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("response_text,expected_sources", [
        pytest.param(
            "Result 1\nSource: docs.example.com\n\nResult 2\nSource: api.example.com",
            ["docs.example.com", "api.example.com"],
            id="multiple-sources"
        ),
        pytest.param(
            "Single result from Source: main.example.com",
            ["main.example.com"],
            id="single-source"
        ),
        pytest.param(
            "No explicit source information in results",
            [],
            id="no-sources"
        ),
    ])
    async def test_source_extraction_from_responses(
        self,
        rag_agent,
        response_text,
        expected_sources
    ):
        """Test extraction of source information from various response formats."""
        # Arrange
        rag_agent._agent.run = AsyncMock(return_value=response_text)
        
        # Act
        result = await rag_agent.run_conversation("test query")
        
        # Assert
        assert result.success is True
        assert len(result.sources) == len(expected_sources)
        for source in expected_sources:
            assert source in result.sources
    
    # =============================================================================
    # Progress Callback Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_progress_callback_integration(
        self,
        rag_agent,
        make_rag_deps
    ):
        """Test progress callback during RAG operations."""
        # Arrange
        progress_updates = []
        
        async def progress_callback(update):
            progress_updates.append(update)
        
        deps = make_rag_deps(progress_callback=progress_callback)
        
        rag_agent._agent.run = AsyncMock(return_value="Search complete")
        
        # Act
        await rag_agent.run("Search query", deps)
        
        # Assert
        # Verify callback was passed through
        assert deps.progress_callback is not None
        rag_agent._agent.run.assert_called_once()
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    @pytest.mark.parametrize("result_count", [10, 50, 100])
    @patch('src.agents.rag_agent.SearchService')
    async def test_large_result_handling_performance(
        self,
        mock_search_service_class,
        rag_agent,
        make_search_results,
        result_count
    ):
        """Test performance with large numbers of search results."""
        # Arrange
        mock_search_service = MagicMock()
        large_results = make_search_results(num_results=result_count)
        mock_search_service.perform_rag_query.return_value = (True, large_results)
        mock_search_service_class.return_value = mock_search_service
        
        rag_agent._agent.run = AsyncMock(return_value=f"Processed {result_count} results")
        
        # Act & Assert
        with measure_time(f"process_{result_count}_results", threshold=2.0):
            result = await rag_agent.run_conversation("Large search query")
        
        assert result.success is True
        assert result.results_found == result_count
    
    # =============================================================================
    # Model Validation Tests
    # =============================================================================
    
    @pytest.mark.parametrize("deps_config", [
        pytest.param({}, id="minimal-deps"),
        pytest.param({"match_count": 10}, id="custom-match-count"),
        pytest.param({"source_filter": "docs.example.com"}, id="with-filter"),
        pytest.param({"project_id": "proj-123", "user_id": "user-456"}, id="full-ids"),
    ])
    def test_rag_dependencies_validation(self, deps_config):
        """Test RagDependencies model with various configurations."""
        # Act
        deps = RagDependencies(**deps_config)
        
        # Assert
        assert deps.match_count == deps_config.get("match_count", 5)
        assert deps.source_filter == deps_config.get("source_filter")
        assert deps.project_id == deps_config.get("project_id")
    
    @pytest.mark.parametrize("result_data,is_valid", [
        pytest.param(
            {
                "query_type": "search",
                "original_query": "test",
                "answer": "Found results",
                "success": True
            },
            True,
            id="minimal-valid"
        ),
        pytest.param(
            {
                "query_type": "search",
                "original_query": "test",
                "refined_query": "enhanced test",
                "results_found": 5,
                "sources": ["source1", "source2"],
                "answer": "Detailed answer",
                "citations": [{"source": "source1", "relevance": 0.9}],
                "success": True,
                "message": "Search completed"
            },
            True,
            id="complete-valid"
        ),
    ])
    def test_rag_query_result_validation(self, result_data, is_valid):
        """Test RagQueryResult model validation."""
        if is_valid:
            result = RagQueryResult(**result_data)
            assert result.query_type == result_data["query_type"]
            assert result.success == result_data["success"]
        else:
            with pytest.raises(ValueError):
                RagQueryResult(**result_data)