"""Unit tests for Tests API endpoints."""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
import uuid
from fastapi import WebSocket
from fastapi.testclient import TestClient
from src.api.tests_api import (
    router, TestExecutionRequest, TestExecutionResponse, TestStatusResponse,
    TestHistoryResponse, TestType, TestStatus, TestExecution, TestWebSocketManager,
    websocket_manager
)


class TestWebSocketManagerTests:
    """Unit tests for TestWebSocketManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create TestWebSocketManager instance."""
        return TestWebSocketManager()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_connect(self, manager):
        """Test WebSocket connection management."""
        execution_id = "test-execution-123"
        
        # Mock WebSocket
        ws = MagicMock()
        ws.accept = AsyncMock()
        
        # Connect WebSocket
        await manager.connect(ws, execution_id)
        
        assert execution_id in manager.connections
        assert ws in manager.connections[execution_id]
        ws.accept.assert_called_once()
    
    @pytest.mark.unit
    def test_websocket_disconnect(self, manager):
        """Test WebSocket disconnection."""
        execution_id = "test-execution-123"
        ws = MagicMock()
        
        # Setup connection
        manager.connections[execution_id] = [ws]
        
        # Disconnect
        manager.disconnect(ws, execution_id)
        
        assert execution_id not in manager.connections
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_broadcast_to_execution(self, manager):
        """Test broadcasting messages to WebSocket clients."""
        execution_id = "test-execution-123"
        
        # Mock WebSockets
        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock(side_effect=Exception("Disconnected"))
        
        manager.connections[execution_id] = [ws1, ws2]
        
        # Broadcast message
        message = {"type": "output", "message": "Test output"}
        await manager.broadcast_to_execution(execution_id, message)
        
        # Check ws1 received message
        ws1.send_json.assert_called_once_with(message)
        # Check ws2 was removed due to error
        assert ws2 not in manager.connections.get(execution_id, [])


class TestTestExecution:
    """Unit tests for TestExecution data class."""
    
    @pytest.mark.unit
    def test_test_execution_creation(self):
        """Test TestExecution creation and defaults."""
        execution = TestExecution(
            execution_id="test-123",
            test_type=TestType.MCP,
            status=TestStatus.PENDING,
            started_at=datetime.now()
        )
        
        assert execution.execution_id == "test-123"
        assert execution.test_type == TestType.MCP
        assert execution.status == TestStatus.PENDING
        assert execution.output_lines == []
        assert execution.completed_at is None
        assert execution.exit_code is None
    
    @pytest.mark.unit
    def test_duration_calculation(self):
        """Test duration calculation property."""
        started = datetime(2024, 1, 1, 10, 0, 0)
        completed = datetime(2024, 1, 1, 10, 5, 30)
        
        execution = TestExecution(
            execution_id="test-123",
            test_type=TestType.UI,
            status=TestStatus.COMPLETED,
            started_at=started,
            completed_at=completed
        )
        
        assert execution.duration_seconds == 330.0  # 5 minutes 30 seconds


class TestTestExecutionFunctions:
    """Unit tests for test execution functions."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('asyncio.create_subprocess_exec')
    @patch('src.api.tests_api.stream_process_output')
    async def test_execute_mcp_tests_success(self, mock_stream, mock_subprocess):
        """Test successful MCP test execution."""
        execution_id = "test-mcp-123"
        
        # Setup test execution
        execution = TestExecution(
            execution_id=execution_id,
            test_type=TestType.MCP,
            status=TestStatus.PENDING,
            started_at=datetime.now()
        )
        
        # Mock process
        mock_process = MagicMock()
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        # Add to global state
        from src.api.tests_api import test_executions
        test_executions[execution_id] = execution
        
        # Execute tests
        from src.api.tests_api import execute_mcp_tests
        result = await execute_mcp_tests(execution_id)
        
        assert result.status == TestStatus.COMPLETED
        assert result.exit_code == 0
        assert result.summary["result"] == "All Python tests passed"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('asyncio.create_subprocess_exec')
    async def test_execute_mcp_tests_failure(self, mock_subprocess):
        """Test failed MCP test execution."""
        execution_id = "test-mcp-456"
        
        # Setup test execution
        execution = TestExecution(
            execution_id=execution_id,
            test_type=TestType.MCP,
            status=TestStatus.PENDING,
            started_at=datetime.now()
        )
        
        # Mock process with failure
        mock_process = MagicMock()
        mock_process.wait = AsyncMock(return_value=1)
        mock_process.stdout.readline = AsyncMock(return_value=b'')
        mock_subprocess.return_value = mock_process
        
        # Add to global state
        from src.api.tests_api import test_executions
        test_executions[execution_id] = execution
        
        # Execute tests
        from src.api.tests_api import execute_mcp_tests
        result = await execute_mcp_tests(execution_id)
        
        assert result.status == TestStatus.FAILED
        assert result.exit_code == 1
        assert "failed" in result.summary["result"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('asyncio.create_subprocess_exec')
    @patch('src.api.tests_api.stream_process_output')
    async def test_execute_ui_tests_success(self, mock_stream, mock_subprocess):
        """Test successful UI test execution."""
        execution_id = "test-ui-123"
        
        # Setup test execution
        execution = TestExecution(
            execution_id=execution_id,
            test_type=TestType.UI,
            status=TestStatus.PENDING,
            started_at=datetime.now()
        )
        
        # Mock process
        mock_process = MagicMock()
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        # Add to global state
        from src.api.tests_api import test_executions
        test_executions[execution_id] = execution
        
        # Execute tests
        from src.api.tests_api import execute_ui_tests
        result = await execute_ui_tests(execution_id)
        
        assert result.status == TestStatus.COMPLETED
        assert result.exit_code == 0
        assert "React UI tests passed" in result.summary["result"]


class TestTestsAPIEndpoints:
    """Unit tests for Tests API endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def cleanup_executions(self):
        """Cleanup test executions after test."""
        yield
        from src.api.tests_api import test_executions
        test_executions.clear()
    
    @pytest.mark.unit
    def test_run_mcp_tests_endpoint(self, test_client, cleanup_executions):
        """Test POST /mcp/run endpoint."""
        request_data = {"test_type": "mcp", "options": {}}
        
        response = test_client.post("/api/tests/mcp/run", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["test_type"] == "mcp"
        assert data["status"] == "pending"
        assert "execution_id" in data
        assert data["message"] == "Python test execution started"
    
    @pytest.mark.unit
    def test_run_ui_tests_endpoint(self, test_client, cleanup_executions):
        """Test POST /ui/run endpoint."""
        request_data = {"test_type": "ui", "options": {}}
        
        response = test_client.post("/api/tests/ui/run", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["test_type"] == "ui"
        assert data["status"] == "pending"
        assert "execution_id" in data
        assert data["message"] == "React UI test execution started"
    
    @pytest.mark.unit
    def test_get_test_status_endpoint(self, test_client, cleanup_executions):
        """Test GET /status/{execution_id} endpoint."""
        # Create test execution
        execution_id = "test-status-123"
        from src.api.tests_api import test_executions
        test_executions[execution_id] = TestExecution(
            execution_id=execution_id,
            test_type=TestType.MCP,
            status=TestStatus.RUNNING,
            started_at=datetime.now()
        )
        
        response = test_client.get(f"/api/tests/status/{execution_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == execution_id
        assert data["test_type"] == "mcp"
        assert data["status"] == "running"
    
    @pytest.mark.unit
    def test_get_test_status_not_found(self, test_client):
        """Test GET /status/{execution_id} with non-existent ID."""
        response = test_client.get("/api/tests/status/non-existent-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @pytest.mark.unit
    def test_get_test_history_endpoint(self, test_client, cleanup_executions):
        """Test GET /history endpoint."""
        # Create test executions
        from src.api.tests_api import test_executions
        
        for i in range(5):
            exec_id = f"test-history-{i}"
            test_executions[exec_id] = TestExecution(
                execution_id=exec_id,
                test_type=TestType.MCP if i % 2 == 0 else TestType.UI,
                status=TestStatus.COMPLETED,
                started_at=datetime.now()
            )
        
        response = test_client.get("/api/tests/history?limit=3&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5
        assert len(data["executions"]) == 3
    
    @pytest.mark.unit
    def test_test_execution_request_validation(self):
        """Test TestExecutionRequest model validation."""
        # Valid request
        request = TestExecutionRequest(test_type=TestType.MCP)
        assert request.test_type == TestType.MCP
        assert request.options == {}
        
        # Request with options
        request2 = TestExecutionRequest(
            test_type=TestType.UI,
            options={"verbose": True}
        )
        assert request2.test_type == TestType.UI
        assert request2.options["verbose"] is True
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stream_process_output(self):
        """Test process output streaming function."""
        execution_id = "test-stream-123"
        
        # Setup execution
        from src.api.tests_api import test_executions
        execution = TestExecution(
            execution_id=execution_id,
            test_type=TestType.MCP,
            status=TestStatus.RUNNING,
            started_at=datetime.now()
        )
        test_executions[execution_id] = execution
        
        # Mock process
        mock_process = MagicMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[
            b'Test line 1\n',
            b'Test line 2\n',
            b''  # EOF
        ])
        mock_process.returncode = None
        
        # Mock websocket manager
        with patch('src.api.tests_api.websocket_manager') as mock_ws_manager:
            mock_ws_manager.broadcast_to_execution = AsyncMock()
            
            # Stream output
            from src.api.tests_api import stream_process_output
            await stream_process_output(execution_id, mock_process)
            
            # Verify output was captured
            assert len(execution.output_lines) == 2
            assert execution.output_lines[0] == "Test line 1"
            assert execution.output_lines[1] == "Test line 2"
            
            # Verify broadcasts were made
            assert mock_ws_manager.broadcast_to_execution.call_count >= 3  # Initial status + 2 lines
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_execute_tests_background(self):
        """Test background task execution."""
        execution_id = "test-bg-123"
        
        # Setup execution
        from src.api.tests_api import test_executions
        execution = TestExecution(
            execution_id=execution_id,
            test_type=TestType.MCP,
            status=TestStatus.PENDING,
            started_at=datetime.now()
        )
        test_executions[execution_id] = execution
        
        # Mock execution functions
        with patch('src.api.tests_api.execute_mcp_tests') as mock_mcp:
            mock_mcp.return_value = AsyncMock()
            
            from src.api.tests_api import execute_tests_background
            await execute_tests_background(execution_id, TestType.MCP)
            
            mock_mcp.assert_called_once_with(execution_id)