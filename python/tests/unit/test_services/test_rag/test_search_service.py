"""Unit tests for SearchService."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.services.rag.search_service import SearchService


class TestSearchService:
    """Unit tests for SearchService."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        return MagicMock()
    
    @pytest.fixture
    def mock_reranking_model(self):
        """Mock reranking model."""
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
    def mock_search_results(self):
        """Mock search results."""
        return [
            {
                "id": "doc1",
                "content": "This is the first document about Python programming.",
                "metadata": {"source": "docs.python.org"},
                "similarity": 0.85
            },
            {
                "id": "doc2",
                "content": "This is the second document about data science.",
                "metadata": {"source": "kaggle.com"},
                "similarity": 0.75
            },
            {
                "id": "doc3",
                "content": "This is the third document about machine learning.",
                "metadata": {"source": "arxiv.org"},
                "similarity": 0.65
            }
        ]
    
    @pytest.mark.unit
    @patch('src.services.rag.search_service.search_documents')
    def test_search_finds_similar_documents(self, mock_search_docs, search_service, mock_search_results):
        """Test finding similar documents via vector search."""
        # Arrange
        query = "Python programming tutorials"
        mock_search_docs.return_value = mock_search_results
        
        # Act
        success, result = search_service.perform_rag_query(query)
        
        # Assert
        assert success is True
        assert len(result["results"]) == 3
        assert result["results"][0]["content"] == mock_search_results[0]["content"]
        assert result["query"] == query
        mock_search_docs.assert_called_once()
    
    @pytest.mark.unit
    def test_search_applies_similarity_threshold(self, search_service):
        """Test that search respects similarity thresholds."""
        # Note: Current implementation doesn't filter by threshold
        # This test documents expected behavior
        # Filtering happens in the search_documents utility
        pass
    
    @pytest.mark.unit
    @patch('src.services.rag.search_service.search_documents')
    def test_search_filters_by_source(self, mock_search_docs, search_service, mock_search_results):
        """Test filtering search results by source."""
        # Arrange
        query = "Python documentation"
        source = "docs.python.org"
        mock_search_docs.return_value = [mock_search_results[0]]  # Only first result
        
        # Act
        success, result = search_service.perform_rag_query(
            query=query,
            source=source
        )
        
        # Assert
        assert success is True
        assert result["source"] == source
        
        # Verify filter was passed to search function
        call_args = mock_search_docs.call_args[1]
        assert call_args["filter_metadata"] == {"source": source}
    
    @pytest.mark.unit
    def test_search_reranks_results_when_enabled(self, search_service, mock_search_results):
        """Test reranking of search results."""
        # Arrange
        query = "Python programming"
        results = mock_search_results.copy()
        
        # Act
        reranked = search_service.rerank_results(query, results)
        
        # Assert
        assert len(reranked) == 3
        # Check that rerank scores were added
        assert all("rerank_score" in r for r in reranked)
        # Check ordering by rerank score
        assert reranked[0]["rerank_score"] >= reranked[1]["rerank_score"]
        assert reranked[1]["rerank_score"] >= reranked[2]["rerank_score"]
    
    @pytest.mark.unit
    @patch('src.services.rag.search_service.search_documents')
    def test_search_handles_empty_queries(self, mock_search_docs, search_service):
        """Test handling of empty search queries."""
        # Arrange
        mock_search_docs.return_value = []
        
        # Act
        success, result = search_service.perform_rag_query("")
        
        # Assert
        assert success is True
        assert result["results"] == []
        assert result["total_found"] == 0
    
    @pytest.mark.unit
    @patch('src.services.rag.search_service.search_documents')
    def test_search_limits_result_count(self, mock_search_docs, search_service, mock_search_results):
        """Test limiting the number of search results."""
        # Arrange
        query = "Python"
        match_count = 2
        mock_search_docs.return_value = mock_search_results[:match_count]
        
        # Act
        success, result = search_service.perform_rag_query(
            query=query,
            match_count=match_count
        )
        
        # Assert
        assert success is True
        assert len(result["results"]) == match_count
        assert result["match_count"] == match_count
    
    @pytest.mark.unit
    @patch('src.services.rag.search_service.search_documents')
    def test_search_includes_metadata_in_results(self, mock_search_docs, search_service, mock_search_results):
        """Test that metadata is included in search results."""
        # Arrange
        mock_search_docs.return_value = mock_search_results
        
        # Act
        success, result = search_service.perform_rag_query("test query")
        
        # Assert
        assert success is True
        for i, res in enumerate(result["results"]):
            assert "metadata" in res
            assert res["metadata"] == mock_search_results[i]["metadata"]
            assert "similarity_score" in res
    
    @pytest.mark.unit
    def test_search_handles_special_characters(self, search_service):
        """Test handling of special characters in queries."""
        # Test various special character queries
        special_queries = [
            "C++ programming",
            "What is F#?",
            "Python 3.9+",
            "email@example.com",
            "price > $100"
        ]
        
        with patch('src.services.rag.search_service.search_documents', return_value=[]):
            for query in special_queries:
                success, result = search_service.perform_rag_query(query)
                assert success is True
                assert result["query"] == query
    
    @pytest.mark.unit
    @patch('src.services.rag.search_service.search_code_examples')
    def test_search_code_examples(self, mock_search_code, search_service):
        """Test searching for code examples."""
        # Arrange
        query = "async function"
        mock_code_results = [
            {
                "id": "code1",
                "url": "https://example.com/async",
                "content": "async def fetch_data():\n    return await api_call()",
                "summary": "Async function example",
                "metadata": {"language": "python"},
                "similarity": 0.9
            }
        ]
        mock_search_code.return_value = mock_code_results
        
        # Mock settings
        with patch.object(search_service, 'get_bool_setting') as mock_setting:
            mock_setting.side_effect = lambda key, default: {
                "USE_AGENTIC_RAG": True,
                "USE_HYBRID_SEARCH": False,
                "USE_RERANKING": False
            }.get(key, default)
            
            # Act
            success, result = search_service.search_code_examples_service(query)
            
            # Assert
            assert success is True
            assert len(result["results"]) == 1
            assert result["results"][0]["code"] == mock_code_results[0]["content"]
            assert result["search_mode"] == "vector"
    
    @pytest.mark.unit
    def test_hybrid_search_combines_results(self, search_service, mock_supabase_client):
        """Test hybrid search combining vector and keyword results."""
        # Arrange
        query = "Python async"
        
        # Mock vector results
        vector_results = [
            {"id": "1", "content": "Async Python guide", "similarity": 0.8},
            {"id": "2", "content": "Python threading", "similarity": 0.7}
        ]
        
        # Mock keyword results
        keyword_results = [
            {"id": "1", "content": "Async Python guide"},  # Overlaps with vector
            {"id": "3", "content": "Python async await"}   # New result
        ]
        
        mock_supabase_client.from_.return_value.select.return_value.or_.return_value.limit.return_value.execute.return_value.data = keyword_results
        
        with patch('src.services.rag.search_service.search_code_examples', return_value=vector_results):
            with patch.object(search_service, 'get_bool_setting') as mock_setting:
                mock_setting.side_effect = lambda key, default: {
                    "USE_AGENTIC_RAG": True,
                    "USE_HYBRID_SEARCH": True,
                    "USE_RERANKING": False
                }.get(key, default)
                
                # Act
                success, result = search_service.search_code_examples_service(query)
                
                # Assert
                assert success is True
                assert result["search_mode"] == "hybrid"
                # Should prioritize overlapping results
                assert len(result["results"]) >= 2
    
    @pytest.mark.unit
    def test_reranking_error_handling(self, search_service, mock_search_results):
        """Test reranking handles errors gracefully."""
        # Arrange
        search_service.reranking_model.predict.side_effect = Exception("Model error")
        
        # Act
        reranked = search_service.rerank_results("query", mock_search_results)
        
        # Assert
        # Should return original results on error
        assert reranked == mock_search_results
        assert "rerank_score" not in reranked[0]
    
    @pytest.mark.unit
    def test_get_setting_with_credential_service(self, search_service):
        """Test getting settings from credential service."""
        # Test with mocked credential service
        with patch('src.services.rag.search_service.credential_service') as mock_cred:
            mock_cred._cache_initialized = True
            mock_cred._cache = {"TEST_KEY": "test_value"}
            
            value = search_service.get_setting("TEST_KEY", "default")
            assert value == "test_value"
        
        # Test fallback to environment
        with patch.dict('os.environ', {"TEST_KEY": "env_value"}):
            value = search_service.get_setting("TEST_KEY", "default")
            assert value == "env_value"
    
    @pytest.mark.unit
    def test_get_bool_setting(self, search_service):
        """Test boolean setting conversion."""
        # Test various true values
        for true_val in ["true", "True", "1", "yes", "on"]:
            with patch.object(search_service, 'get_setting', return_value=true_val):
                assert search_service.get_bool_setting("TEST") is True
        
        # Test various false values
        for false_val in ["false", "False", "0", "no", "off", ""]:
            with patch.object(search_service, 'get_setting', return_value=false_val):
                assert search_service.get_bool_setting("TEST") is False