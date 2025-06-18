"""
MCP API endpoints for Archon

Handles:
- MCP server lifecycle (start/stop/status)
- MCP server configuration management
- WebSocket log streaming
- Tool discovery and testing
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import subprocess
import os
import time
from collections import deque
from datetime import datetime
import json
import aiohttp

from ..utils import get_supabase_client

# Import Logfire
from ..logfire_config import mcp_logger, api_logger

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

class ServerConfig(BaseModel):
    transport: str = 'sse'
    host: str = 'localhost'
    port: int = 8051

class ServerResponse(BaseModel):
    success: bool
    message: str
    status: Optional[str] = None
    pid: Optional[int] = None

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str

class MCPServerManager:
    """Manages the MCP server process lifecycle."""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.status: str = 'stopped'
        self.start_time: Optional[float] = None
        self.logs: deque = deque(maxlen=1000)  # Keep last 1000 log entries
        self.log_websockets: List[WebSocket] = []
        self.log_reader_task: Optional[asyncio.Task] = None
        self._operation_lock = asyncio.Lock()  # Prevent concurrent start/stop operations
        self._last_operation_time = 0
        self._min_operation_interval = 2.0  # Minimum 2 seconds between operations
    
    async def start_server(self) -> Dict[str, Any]:
        """Start the MCP server process."""
        async with self._operation_lock:
            # Check throttling
            current_time = time.time()
            if current_time - self._last_operation_time < self._min_operation_interval:
                wait_time = self._min_operation_interval - (current_time - self._last_operation_time)
                mcp_logger.warning(f"Start operation throttled, please wait {wait_time:.1f}s")
                return {
                    'success': False,
                    'status': self.status,
                    'message': f'Please wait {wait_time:.1f}s before starting server again'
                }
            
        with mcp_logger.span("mcp_server_start") as span:
            span.set_attribute("action", "start_server")
            
            if self.process and self.process.poll() is None:
                mcp_logger.warning("MCP server start attempted while already running")
                return {
                    'success': False,
                    'status': self.status,
                    'message': 'MCP server is already running'
                }
            
            try:
                # Set up environment variables for the MCP server
                env = os.environ.copy()
                
                # Fixed configuration for SSE-only mode
                transport = 'sse'
                host = '0.0.0.0'
                port = '8051'
                
                # Get only essential credentials from database
                from ..credential_service import credential_service
                await credential_service.load_all_credentials()
                model_choice = await credential_service.get_credential('MODEL_CHOICE', 'gpt-4o-mini')
                openai_key = await credential_service.get_credential('OPENAI_API_KEY', '')
                
                # Update environment with values
                env.update({
                    'MODEL_CHOICE': str(model_choice),
                    'OPENAI_API_KEY': str(openai_key) if openai_key else env.get('OPENAI_API_KEY', '')
                })
                
                # Verify and log key environment variables
                openai_key_found = bool(env.get('OPENAI_API_KEY'))
                
                # Ensure Supabase environment variables are available
                env.update({
                    'SUPABASE_URL': os.getenv('SUPABASE_URL', ''),
                    'SUPABASE_SERVICE_KEY': os.getenv('SUPABASE_SERVICE_KEY', ''),
                })
                
                # Debug logging
                self._add_log('INFO', f'MCP server environment - OpenAI key: {"Found" if openai_key_found else "Not found"}')
                self._add_log('INFO', f'Configuration: SSE-only mode, host={host}, port={port}, model={model_choice}')
                
                mcp_logger.info("MCP server configuration", 
                              mode="SSE-only", host=host, port=port, model=model_choice, 
                              openai_key_available=openai_key_found)
                
                # Start the MCP server process (using uv like the old working version)
                cmd = ['uv', 'run', 'python', 'src/mcp_server.py']
                self.process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1  # Line buffered
                )
                
                self.status = 'starting'
                self.start_time = time.time()
                self._last_operation_time = time.time()
                self._add_log('INFO', 'MCP server starting...')
                mcp_logger.info("MCP server process started", pid=self.process.pid, cmd=cmd)
                span.set_attribute("pid", self.process.pid)
                
                # Start reading logs from the process
                self.log_reader_task = asyncio.create_task(self._read_process_logs())
                
                # Give it a moment to start
                await asyncio.sleep(2)
                
                # Check if process is still running
                if self.process.poll() is None:
                    self.status = 'running'
                    self._add_log('INFO', 'MCP server started successfully')
                    mcp_logger.info("MCP server started successfully", pid=self.process.pid, uptime=0)
                    span.set_attribute("success", True)
                    span.set_attribute("status", "running")
                    return {
                        'success': True,
                        'status': self.status,
                        'message': 'MCP server started successfully',
                        'pid': self.process.pid
                    }
                else:
                    self.status = 'failed'
                    self._add_log('ERROR', 'MCP server failed to start')
                    mcp_logger.error("MCP server failed to start - process exited immediately")
                    span.set_attribute("success", False)
                    span.set_attribute("status", "failed")
                    return {
                        'success': False,
                        'status': self.status,
                        'message': 'MCP server failed to start'
                    }
                    
            except Exception as e:
                self.status = 'failed'
                self._add_log('ERROR', f'Failed to start MCP server: {str(e)}')
                mcp_logger.error("Exception during MCP server startup", error=str(e), error_type=type(e).__name__)
                span.set_attribute("success", False)
                span.set_attribute("error", str(e))
                return {
                    'success': False,
                    'status': self.status,
                    'message': f'Failed to start MCP server: {str(e)}'
                }
    
    async def stop_server(self) -> Dict[str, Any]:
        """Stop the MCP server process."""
        async with self._operation_lock:
            # Check throttling
            current_time = time.time()
            if current_time - self._last_operation_time < self._min_operation_interval:
                wait_time = self._min_operation_interval - (current_time - self._last_operation_time)
                mcp_logger.warning(f"Stop operation throttled, please wait {wait_time:.1f}s")
                return {
                    'success': False,
                    'status': self.status,
                    'message': f'Please wait {wait_time:.1f}s before stopping server again'
                }
                
        with mcp_logger.span("mcp_server_stop") as span:
            span.set_attribute("action", "stop_server")
            
            if not self.process or self.process.poll() is not None:
                mcp_logger.warning("MCP server stop attempted when not running")
                return {
                    'success': False,
                    'status': 'stopped',
                    'message': 'MCP server is not running'
                }
            
            try:
                self.status = 'stopping'
                self._add_log('INFO', 'Stopping MCP server...')
                mcp_logger.info("Stopping MCP server", pid=self.process.pid)
                span.set_attribute("pid", self.process.pid)
                
                # Cancel log reading task
                if self.log_reader_task:
                    self.log_reader_task.cancel()
                    try:
                        await self.log_reader_task
                    except asyncio.CancelledError:
                        pass
                
                # Terminate the process
                self.process.terminate()
                
                # Wait for process to exit (with timeout)
                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, self.process.wait),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    # Force kill if it doesn't exit gracefully
                    self.process.kill()
                    await asyncio.get_event_loop().run_in_executor(None, self.process.wait)
                    mcp_logger.warning("MCP server force killed after timeout")
                
                self.process = None
                self.status = 'stopped'
                self.start_time = None
                self._last_operation_time = time.time()
                self._add_log('INFO', 'MCP server stopped')
                mcp_logger.info("MCP server stopped successfully")
                span.set_attribute("success", True)
                span.set_attribute("status", "stopped")
                
                return {
                    'success': True,
                    'status': self.status,
                    'message': 'MCP server stopped successfully'
                }
                
            except Exception as e:
                self._add_log('ERROR', f'Error stopping MCP server: {str(e)}')
                mcp_logger.error("Exception during MCP server stop", error=str(e), error_type=type(e).__name__)
                span.set_attribute("success", False)
                span.set_attribute("error", str(e))
                return {
                    'success': False,
                    'status': self.status,
                    'message': f'Error stopping MCP server: {str(e)}'
                }
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current server status."""
        if self.process:
            if self.process.poll() is None:
                self.status = 'running'
            else:
                self.status = 'stopped'
                self.process = None
        
        uptime = None
        if self.status == 'running' and self.start_time:
            uptime = int(time.time() - self.start_time)
        
        # Convert log entries to strings for backward compatibility
        recent_logs = []
        for log in list(self.logs)[-10:]:
            if isinstance(log, dict):
                recent_logs.append(f"[{log['level']}] {log['message']}")
            else:
                recent_logs.append(str(log))
        
        return {
            'status': self.status,
            'uptime': uptime,
            'logs': recent_logs
        }
    
    def _add_log(self, level: str, message: str):
        """Add a log entry and broadcast to connected WebSockets."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level,
            'message': message
        }
        self.logs.append(log_entry)
        
        # Broadcast to all connected WebSockets
        asyncio.create_task(self._broadcast_log(log_entry))
    
    async def _broadcast_log(self, log_entry: Dict[str, Any]):
        """Broadcast log entry to all connected WebSockets."""
        disconnected = []
        for ws in self.log_websockets:
            try:
                await ws.send_json(log_entry)
            except Exception:
                disconnected.append(ws)
        
        # Remove disconnected WebSockets
        for ws in disconnected:
            self.log_websockets.remove(ws)
    
    async def _read_process_logs(self):
        """Read logs from process stdout/stderr."""
        if not self.process:
            return
        
        async def read_stream(stream, is_stderr=False):
            while True:
                try:
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, stream.readline
                    )
                    if not line:
                        break
                    
                    line = line.strip()
                    if line:
                        level, message = self._parse_log_line(line)
                        # Only mark stderr as ERROR if it's not already parsed as something else
                        if is_stderr and level == 'INFO' and not any(
                            keyword in line.lower() for keyword in 
                            ['info:', 'downloading', 'building', 'installed', 'creating', 'using cpython', 'uvicorn running']
                        ):
                            # Check if it looks like an actual error
                            if any(err in line.lower() for err in ['error', 'exception', 'failed', 'critical']):
                                level = 'ERROR'
                        self._add_log(level, message)
                except Exception as e:
                    self._add_log('ERROR', f'Log reading error: {str(e)}')
                    break
        
        # Read both stdout and stderr concurrently
        try:
            await asyncio.gather(
                read_stream(self.process.stdout),
                read_stream(self.process.stderr, is_stderr=True)
            )
        except asyncio.CancelledError:
            pass
        finally:
            # Process has ended
            if self.process and self.process.poll() is not None:
                self._add_log('INFO', f'MCP server process terminated with code {self.process.returncode}')
    
    def _parse_log_line(self, line: str) -> tuple[str, str]:
        """Parse a log line to extract level and message."""
        line = line.strip()
        if not line:
            return 'INFO', ''
        
        # Try to extract log level from common formats
        if line.startswith('[') and ']' in line:
            end_bracket = line.find(']')
            potential_level = line[1:end_bracket].upper()
            if potential_level in ['INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL']:
                return potential_level, line[end_bracket+1:].strip()
        
        # Check for common log level indicators
        line_lower = line.lower()
        if any(word in line_lower for word in ['error', 'exception', 'failed', 'critical']):
            return 'ERROR', line
        elif any(word in line_lower for word in ['warning', 'warn']):
            return 'WARNING', line
        elif any(word in line_lower for word in ['debug']):
            return 'DEBUG', line
        else:
            return 'INFO', line
    
    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical logs."""
        logs = list(self.logs)
        if limit > 0:
            logs = logs[-limit:]
        return logs
    
    def clear_logs(self):
        """Clear the log buffer."""
        self.logs.clear()
        self._add_log('INFO', 'Logs cleared')
    
    async def add_websocket(self, websocket: WebSocket):
        """Add a WebSocket connection for log streaming."""
        await websocket.accept()
        self.log_websockets.append(websocket)
        
        # Send connection info but NOT historical logs
        # The frontend already fetches historical logs via the /logs endpoint
        await websocket.send_json({
            "type": "connection",
            "message": "WebSocket connected for log streaming"
        })
    
    def remove_websocket(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.log_websockets:
            self.log_websockets.remove(websocket)

# Global MCP manager instance
mcp_manager = MCPServerManager()

@router.post("/start", response_model=ServerResponse)
async def start_server():
    """Start the MCP server."""
    with api_logger.span("api_mcp_start") as span:
        span.set_attribute("endpoint", "/mcp/start")
        span.set_attribute("method", "POST")
        
        try:
            result = await mcp_manager.start_server()
            api_logger.info("MCP server start API called", success=result.get('success', False))
            span.set_attribute("success", result.get('success', False))
            return result
        except Exception as e:
            api_logger.error("MCP server start API failed", error=str(e))
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop", response_model=ServerResponse)
async def stop_server():
    """Stop the MCP server."""
    with api_logger.span("api_mcp_stop") as span:
        span.set_attribute("endpoint", "/mcp/stop")
        span.set_attribute("method", "POST")
        
        try:
            result = await mcp_manager.stop_server()
            api_logger.info("MCP server stop API called", success=result.get('success', False))
            span.set_attribute("success", result.get('success', False))
            return result
        except Exception as e:
            api_logger.error("MCP server stop API failed", error=str(e))
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_status():
    """Get MCP server status."""
    with api_logger.span("api_mcp_status") as span:
        span.set_attribute("endpoint", "/mcp/status")
        span.set_attribute("method", "GET")
        
        try:
            status = mcp_manager.get_status()
            api_logger.debug("MCP server status checked", status=status.get('status'))
            span.set_attribute("status", status.get('status'))
            span.set_attribute("uptime", status.get('uptime'))
            return status
        except Exception as e:
            api_logger.error("MCP server status API failed", error=str(e))
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs")
async def get_logs(limit: int = 100):
    """Get MCP server logs."""
    with api_logger.span("api_mcp_logs") as span:
        span.set_attribute("endpoint", "/mcp/logs")
        span.set_attribute("method", "GET")
        span.set_attribute("limit", limit)
        
        try:
            logs = mcp_manager.get_logs(limit)
            api_logger.debug("MCP server logs retrieved", count=len(logs))
            span.set_attribute("log_count", len(logs))
            return {'logs': logs}
        except Exception as e:
            api_logger.error("MCP server logs API failed", error=str(e))
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@router.delete("/logs")
async def clear_logs():
    """Clear MCP server logs."""
    with api_logger.span("api_mcp_clear_logs") as span:
        span.set_attribute("endpoint", "/mcp/logs")
        span.set_attribute("method", "DELETE")
        
        try:
            mcp_manager.clear_logs()
            api_logger.info("MCP server logs cleared")
            span.set_attribute("success", True)
            return {'success': True, 'message': 'Logs cleared successfully'}
        except Exception as e:
            api_logger.error("MCP server clear logs API failed", error=str(e))
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_mcp_config():
    """Get MCP server configuration."""
    with api_logger.span("api_get_mcp_config") as span:
        span.set_attribute("endpoint", "/api/mcp/config")
        span.set_attribute("method", "GET")
        
        try:
            api_logger.info("Getting MCP server configuration")
            
            # Fixed configuration for SSE-only mode
            config = {
                'host': 'localhost',
                'port': 8051,
                'transport': 'sse',
            }
            
            # Get only model choice from database
            try:
                from ..credential_service import credential_service
                model_choice = await credential_service.get_credential('MODEL_CHOICE', 'gpt-4o-mini')
                config['model_choice'] = model_choice
                config['use_contextual_embeddings'] = (await credential_service.get_credential('USE_CONTEXTUAL_EMBEDDINGS', 'false')).lower() == 'true'
                config['use_hybrid_search'] = (await credential_service.get_credential('USE_HYBRID_SEARCH', 'false')).lower() == 'true'
                config['use_agentic_rag'] = (await credential_service.get_credential('USE_AGENTIC_RAG', 'false')).lower() == 'true'
                config['use_reranking'] = (await credential_service.get_credential('USE_RERANKING', 'false')).lower() == 'true'
            except Exception:
                # Fallback to default model
                config['model_choice'] = 'gpt-4o-mini'
                config['use_contextual_embeddings'] = False
                config['use_hybrid_search'] = False
                config['use_agentic_rag'] = False
                config['use_reranking'] = False
            
            api_logger.info("MCP configuration (SSE-only mode)")
            span.set_attribute("host", config['host'])
            span.set_attribute("port", config['port'])
            span.set_attribute("transport", "sse")
            span.set_attribute("model_choice", config.get('model_choice', 'gpt-4o-mini'))
            
            return config
        except Exception as e:
            api_logger.error("Failed to get MCP configuration", error=str(e))
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail={'error': str(e)})

@router.post("/config")
async def save_configuration(config: ServerConfig):
    """Save MCP server configuration."""
    with api_logger.span("api_save_mcp_config") as span:
        span.set_attribute("endpoint", "/api/mcp/config")
        span.set_attribute("method", "POST")
        span.set_attribute("transport", config.transport)
        span.set_attribute("host", config.host)
        span.set_attribute("port", config.port)
        
        try:
            api_logger.info("Saving MCP server configuration", transport=config.transport, host=config.host, port=config.port)
            supabase_client = get_supabase_client()
            
            config_json = config.model_dump_json()
            
            # Check if config exists
            existing = supabase_client.table("credentials").select("id").eq("key_name", "mcp_config").execute()
            
            if existing.data:
                # Update existing
                response = supabase_client.table("credentials").update({
                    "key_value": config_json
                }).eq("key_name", "mcp_config").execute()
                api_logger.info("MCP configuration updated")
                span.set_attribute("operation", "update")
            else:
                # Insert new
                response = supabase_client.table("credentials").insert({
                    "key_name": "mcp_config",
                    "key_value": config_json
                }).execute()
                api_logger.info("MCP configuration created")
                span.set_attribute("operation", "create")
            
            span.set_attribute("success", True)
            return {"success": True, "message": "Configuration saved"}
            
        except Exception as e:
            api_logger.error("Failed to save MCP configuration", error=str(e))
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail={'error': str(e)})

@router.websocket("/logs/stream")
async def websocket_log_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming MCP server logs."""
    await mcp_manager.add_websocket(websocket)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
            # Check if WebSocket is still connected
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        mcp_manager.remove_websocket(websocket)
    except Exception:
        mcp_manager.remove_websocket(websocket)
        try:
            await websocket.close()
        except:
            pass

@router.get("/tools")
async def get_mcp_tools():
    """Get available MCP tools by querying the running MCP server's registered tools."""
    with api_logger.span("api_get_mcp_tools") as span:
        span.set_attribute("endpoint", "/api/mcp/tools")
        span.set_attribute("method", "GET")
        
        try:
            api_logger.info("Getting MCP tools from registered server instance")
            
            # Check if server is running
            server_status = mcp_manager.get_status()
            is_running = server_status.get('status') == 'running'
            span.set_attribute("server_running", is_running)
            
            if not is_running:
                api_logger.warning("MCP server not running when requesting tools")
                return {
                    'tools': [],
                    'count': 0,
                    'server_running': False,
                    'source': 'server_not_running',
                    'message': 'MCP server is not running. Start the server to see available tools.'
                }

            # SIMPLE DEBUG: Just check if we can see any tools at all
            try:
                # Try to inspect the process to see what tools exist
                api_logger.info("Debugging: Attempting to check MCP server tools")
                
                # For now, just return the known modules info since server is registering them
                # This will at least show the UI that tools exist while we debug the real issue
                if is_running:
                    return {
                        'tools': [
                            {"name": "debug_placeholder", "description": "MCP server is running and modules are registered, but tool introspection is not working yet", "module": "debug", "parameters": []}
                        ],
                        'count': 1,
                        'server_running': True,
                        'source': 'debug_placeholder',
                        'message': 'MCP server is running with 3 modules registered. Tool introspection needs to be fixed.'
                    }
                else:
                    return {
                        'tools': [],
                        'count': 0,
                        'server_running': False,
                        'source': 'server_not_running',
                        'message': 'MCP server is not running. Start the server to see available tools.'
                    }
                            
            except Exception as e:
                api_logger.error("Failed to debug MCP server tools", error=str(e))
                
                return {
                    'tools': [],
                    'count': 0,
                    'server_running': is_running,
                    'source': 'debug_error',
                    'message': f'Debug failed: {str(e)}'
                }
        
        except Exception as e:
            api_logger.error("Failed to get MCP tools", error=str(e))
            span.set_attribute("error", str(e))
            span.set_attribute("source", "general_error")
            
            return {
                'tools': [],
                'count': 0,
                'server_running': False,
                'source': 'general_error', 
                'message': f'Error retrieving MCP tools: {str(e)}'
            }

@router.get("/health")
async def mcp_health():
    """Health check for MCP API."""
    with api_logger.span("api_mcp_health") as span:
        span.set_attribute("endpoint", "/api/mcp/health")
        span.set_attribute("method", "GET")
        
        api_logger.info("MCP health check requested")
        result = {"status": "healthy", "service": "mcp"}
        span.set_attribute("status", "healthy")
        
        return result 
