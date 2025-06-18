"""Unit tests for SearchService with enhanced patterns and parametrization."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any, Optional

from src.services.rag.search_service import SearchService
from tests.fixtures.mock_data import IDGenerator
from tests.fixtures.test_helpers import (
    assert_fields_equal,
    assert_called_with_subset,
    measure_time
)


@pytest.mark.unit
@pytest.mark.critical
class TestSearchService:
    """Unit tests for SearchService with enhanced patterns."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        client = MagicMock()
        # Setup chain for query building
        client.from_.return_value.select.return_value.or_.return_value.limit.return_value.execute.return_value.data = []
        return client
    
    @pytest.fixture
    def mock_reranking_model(self):
        """Mock reranking model with predictable scores."""
        model = MagicMock()
        model.predict = MagicMock(return_value=[0.9, 0.7, 0.5])
        return model
    
    @pytest.fixture
    def search_service(self, mock_supabase_client, mock_reranking_model):
        """Create SearchService instance with mocked dependencies."""
        return SearchService(
            supabase_client=mock_supabase_client,
            reranking_model=mock_reranking_model
        )
    
    @pytest.fixture
    def make_search_result(self):
        """Factory for creating mock search results."""
        def _make_result(
            doc_id: str,
            content: str,
            similarity: float = 0.8,
            source: Optional[str] = None,
            metadata: Optional[Dict] = None
        ) -> Dict:
            return {
                "id": doc_id,
                "content": content,
                "metadata": metadata or {"source": source or "test_source"},
                "similarity": similarity
            }
        return _make_result
    
    @pytest.fixture
    def make_search_results(self, make_search_result):
        """Factory for creating lists of search results."""
        def _make_results(count: int, base_similarity: float = 0.9) -> List[Dict]:
            results = []
            for i in range(count):
                results.append(make_search_result(
                    doc_id=f"doc{i+1}",
                    content=f"Document {i+1} content about topic {i+1}",
                    similarity=base_similarity - (i * 0.1)
                ))
            return results
        return _make_results
    
    # =============================================================================
    # Vector Search Tests
    # =============================================================================
    
    @pytest.mark.parametrize("query,expected_results", [
        pytest.param("Python programming", 3, id="standard-query"),
        pytest.param("machine learning algorithms", 5, id="technical-query"),
        pytest.param("", 0, id="empty-query"),
        pytest.param("a" * 1000, 3, id="long-query"),
    ])
    @patch('src.services.rag.search_service.search_documents')
    def test_vector_search_various_queries(
        self,
        mock_search_docs,
        search_service,
        make_search_results,
        query,
        expected_results
    ):
        """Test vector search with various query types."""
        # Arrange
        if expected_results > 0:
            mock_search_docs.return_value = make_search_results(expected_results)
        else:
            mock_search_docs.return_value = []
        
        # Act
        success, result = search_service.perform_rag_query(query)
        
        # Assert
        assert success is True
        assert len(result["results"]) == expected_results
        assert result["query"] == query
        
        if expected_results > 0:
            mock_search_docs.assert_called_once()
            # Verify results are ordered by similarity
            similarities = [r["similarity_score"] for r in result["results"]]
            assert similarities == sorted(similarities, reverse=True)
    
    # =============================================================================
    # Filtering Tests
    # =============================================================================
    
    @pytest.mark.parametrize("source,expected_filter", [
        pytest.param(
            "docs.python.org",
            {"source": "docs.python.org"},
            id="python-docs-source"
        ),
        pytest.param(
            "arxiv.org",
            {"source": "arxiv.org"},
            id="arxiv-source"
        ),
        pytest.param(
            None,
            None,
            id="no-filter"
        ),
    ])
    @patch('src.services.rag.search_service.search_documents')
    def test_search_with_source_filter(
        self,
        mock_search_docs,
        search_service,
        make_search_results,
        source,
        expected_filter
    ):
        """Test search with source filtering."""
        # Arrange
        mock_search_docs.return_value = make_search_results(2)
        
        # Act
        success, result = search_service.perform_rag_query(
            query="test query",
            source=source
        )
        
        # Assert
        assert success is True
        mock_search_docs.assert_called_once()
        
        # Verify filter was passed correctly
        call_kwargs = mock_search_docs.call_args[1]
        if expected_filter:
            assert "filter_metadata" in call_kwargs
            assert call_kwargs["filter_metadata"] == expected_filter
        else:
            assert call_kwargs.get("filter_metadata") is None
    
    # =============================================================================
    # Result Limiting Tests
    # =============================================================================
    
    @pytest.mark.parametrize("total_results,match_count,expected_count", [
        pytest.param(10, 5, 5, id="limit-half"),
        pytest.param(3, 10, 3, id="limit-exceeds-results"),
        pytest.param(20, 1, 1, id="limit-one"),
        pytest.param(0, 10, 0, id="no-results"),
    ])
    @patch('src.services.rag.search_service.search_documents')
    def test_result_limiting(
        self,
        mock_search_docs,
        search_service,
        make_search_results,
        total_results,
        match_count,
        expected_count
    ):
        """Test limiting search results."""
        # Arrange
        mock_search_docs.return_value = make_search_results(total_results)
        
        # Act
        success, result = search_service.perform_rag_query(
            query="test",
            match_count=match_count
        )
        
        # Assert
        assert success is True
        assert len(result["results"]) == expected_count
        assert result["match_count"] == match_count
        assert result["total_found"] == expected_count
    
    # =============================================================================
    # Reranking Tests
    # =============================================================================
    
    @pytest.mark.parametrize("num_results,rerank_scores", [
        pytest.param(3, [0.9, 0.7, 0.5], id="standard-reranking"),
        pytest.param(5, [0.95, 0.85, 0.75, 0.65, 0.55], id="many-results"),
        pytest.param(1, [0.9], id="single-result"),
    ])
    def test_reranking_various_result_counts(
        self,
        search_service,
        make_search_results,
        num_results,
        rerank_scores
    ):
        """Test reranking with various numbers of results."""
        # Arrange
        results = make_search_results(num_results)
        search_service.reranking_model.predict.return_value = rerank_scores
        
        # Act
        reranked = search_service.rerank_results("test query", results)
        
        # Assert
        assert len(reranked) == num_results
        
        # Verify rerank scores assigned
        for i, result in enumerate(reranked):
            assert "rerank_score" in result
        
        # Verify ordering by rerank score
        for i in range(len(reranked) - 1):
            assert reranked[i]["rerank_score"] >= reranked[i + 1]["rerank_score"]
    
    @pytest.mark.parametrize("error_type", [
        pytest.param(ValueError("Invalid input"), id="value-error"),
        pytest.param(RuntimeError("Model failed"), id="runtime-error"),
        pytest.param(Exception("Unknown error"), id="generic-error"),
    ])
    def test_reranking_error_handling(
        self,
        search_service,
        make_search_results,
        error_type
    ):
        """Test reranking handles various errors gracefully."""
        # Arrange
        results = make_search_results(3)
        search_service.reranking_model.predict.side_effect = error_type
        
        # Act
        reranked = search_service.rerank_results("query", results)
        
        # Assert
        # Should return original results on error
        assert reranked == results
        assert all("rerank_score" not in r for r in reranked)
    
    # =============================================================================
    # Code Example Search Tests
    # =============================================================================
    
    @pytest.mark.parametrize("search_mode,settings", [
        pytest.param(
            "vector",
            {"USE_AGENTIC_RAG": True, "USE_HYBRID_SEARCH": False, "USE_RERANKING": False},
            id="vector-only"
        ),
        pytest.param(
            "hybrid",
            {"USE_AGENTIC_RAG": True, "USE_HYBRID_SEARCH": True, "USE_RERANKING": False},
            id="hybrid-search"
        ),
        pytest.param(
            "vector",
            {"USE_AGENTIC_RAG": True, "USE_HYBRID_SEARCH": False, "USE_RERANKING": True},
            id="vector-with-reranking"
        ),
    ])
    @patch('src.services.rag.search_service.search_code_examples')
    def test_code_search_modes(
        self,
        mock_search_code,
        search_service,
        search_mode,
        settings
    ):
        """Test different code search modes."""
        # Arrange
        mock_code_results = [
            {
                "id": "code1",
                "url": "https://example.com/code",
                "content": "def example():\n    pass",
                "summary": "Example function",
                "metadata": {"language": "python"},
                "similarity": 0.9
            }
        ]
        mock_search_code.return_value = mock_code_results
        
        with patch.object(search_service, 'get_bool_setting') as mock_setting:
            mock_setting.side_effect = lambda key, default: settings.get(key, default)
            
            # Act
            success, result = search_service.search_code_examples_service("test query")
            
            # Assert
            assert success is True
            assert result["search_mode"] == search_mode
            assert len(result["results"]) >= 1
    
    # =============================================================================
    # Hybrid Search Tests
    # =============================================================================
    
    @pytest.mark.parametrize("vector_count,keyword_count,overlap_count", [
        pytest.param(3, 2, 1, id="partial-overlap"),
        pytest.param(5, 5, 5, id="complete-overlap"),
        pytest.param(3, 3, 0, id="no-overlap"),
    ])
    @patch('src.services.rag.search_service.search_code_examples')
    def test_hybrid_search_result_merging(
        self,
        mock_search_code,
        search_service,
        mock_supabase_client,
        make_search_result,
        vector_count,
        keyword_count,
        overlap_count
    ):
        """Test hybrid search merging of vector and keyword results."""
        # Arrange
        # Create vector results
        vector_results = []
        for i in range(vector_count):
            vector_results.append(make_search_result(
                doc_id=f"vec_{i}",
                content=f"Vector result {i}",
                similarity=0.9 - (i * 0.1)
            ))
        
        # Create keyword results with some overlap
        keyword_results = []
        for i in range(overlap_count):
            keyword_results.append({
                "id": f"vec_{i}",  # Same ID as vector result
                "content": f"Vector result {i}"
            })
        for i in range(keyword_count - overlap_count):
            keyword_results.append({
                "id": f"kw_{i}",
                "content": f"Keyword result {i}"
            })
        
        mock_search_code.return_value = vector_results
        mock_supabase_client.from_.return_value.select.return_value.or_.return_value.limit.return_value.execute.return_value.data = keyword_results
        
        with patch.object(search_service, 'get_bool_setting') as mock_setting:
            mock_setting.side_effect = lambda key, default: {
                "USE_AGENTIC_RAG": True,
                "USE_HYBRID_SEARCH": True,
                "USE_RERANKING": False
            }.get(key, default)
            
            # Act
            success, result = search_service.search_code_examples_service("test query")
            
            # Assert
            assert success is True
            assert result["search_mode"] == "hybrid"
            
            # Check that we have the right number of unique results
            unique_ids = set(r["id"] for r in result["results"])
            expected_unique = vector_count + keyword_count - overlap_count
            assert len(unique_ids) == expected_unique
    
    # =============================================================================
    # Special Character Handling Tests
    # =============================================================================
    
    @pytest.mark.parametrize("query", [
        pytest.param("C++ programming", id="plus-plus"),
        pytest.param("What is F#?", id="hash-question"),
        pytest.param("Python 3.9+", id="version-plus"),
        pytest.param("email@example.com", id="email-address"),
        pytest.param("price > $100", id="comparison-dollar"),
        pytest.param("SELECT * FROM users", id="sql-query"),
        pytest.param("function(arg1, arg2)", id="function-call"),
    ])
    @patch('src.services.rag.search_service.search_documents')
    def test_special_character_queries(
        self,
        mock_search_docs,
        search_service,
        query
    ):
        """Test handling of special characters in queries."""
        # Arrange
        mock_search_docs.return_value = []
        
        # Act
        success, result = search_service.perform_rag_query(query)
        
        # Assert
        assert success is True
        assert result["query"] == query
        mock_search_docs.assert_called_once()
    
    # =============================================================================
    # Settings and Configuration Tests
    # =============================================================================
    
    @pytest.mark.parametrize("setting_name,env_value,cache_value,expected", [
        pytest.param("API_KEY", "env_key", None, "env_key", id="env-only"),
        pytest.param("API_KEY", "env_key", "cache_key", "cache_key", id="cache-overrides-env"),
        pytest.param("API_KEY", None, None, "default", id="use-default"),
    ])
    def test_get_setting_priority(
        self,
        search_service,
        setting_name,
        env_value,
        cache_value,
        expected
    ):
        """Test setting retrieval priority: cache > env > default."""
        with patch('src.services.rag.search_service.credential_service') as mock_cred:
            with patch.dict('os.environ', {setting_name: env_value} if env_value else {}):
                if cache_value:
                    mock_cred._cache_initialized = True
                    mock_cred._cache = {setting_name: cache_value}
                else:
                    mock_cred._cache_initialized = False
                
                # Act
                value = search_service.get_setting(setting_name, "default")
                
                # Assert
                assert value == expected
    
    @pytest.mark.parametrize("string_value,expected_bool", [
        pytest.param("true", True, id="lowercase-true"),
        pytest.param("True", True, id="capital-true"),
        pytest.param("TRUE", True, id="uppercase-true"),
        pytest.param("1", True, id="numeric-one"),
        pytest.param("yes", True, id="yes"),
        pytest.param("on", True, id="on"),
        pytest.param("false", False, id="lowercase-false"),
        pytest.param("False", False, id="capital-false"),
        pytest.param("0", False, id="numeric-zero"),
        pytest.param("no", False, id="no"),
        pytest.param("off", False, id="off"),
        pytest.param("", False, id="empty-string"),
        pytest.param("random", False, id="random-string"),
    ])
    def test_bool_setting_conversion(
        self,
        search_service,
        string_value,
        expected_bool
    ):
        """Test boolean setting string conversion."""
        with patch.object(search_service, 'get_setting', return_value=string_value):
            # Act
            result = search_service.get_bool_setting("TEST_SETTING")
            
            # Assert
            assert result == expected_bool
    
    # =============================================================================
    # Performance Tests
    # =============================================================================
    
    @pytest.mark.slow
    @pytest.mark.parametrize("num_results", [100, 500, 1000])
    def test_search_performance_at_scale(
        self,
        search_service,
        make_search_results,
        num_results
    ):
        """Test search performance with large result sets."""
        # Arrange
        large_results = make_search_results(num_results)
        
        # Act & Assert - Test reranking performance
        with measure_time(f"rerank_{num_results}_results", threshold=1.0):
            # Mock predict to return scores quickly
            search_service.reranking_model.predict.return_value = list(
                range(num_results, 0, -1)
            )
            reranked = search_service.rerank_results("test query", large_results)
        
        assert len(reranked) == num_results
    
    # =============================================================================
    # Error Cases and Edge Conditions
    # =============================================================================
    
    @pytest.mark.parametrize("results", [
        pytest.param([], id="empty-results"),
        pytest.param(None, id="none-results"),
    ])
    def test_reranking_edge_cases(
        self,
        search_service,
        results
    ):
        """Test reranking with edge case inputs."""
        # Act
        reranked = search_service.rerank_results("query", results or [])
        
        # Assert
        assert reranked == (results or [])
        search_service.reranking_model.predict.assert_not_called()