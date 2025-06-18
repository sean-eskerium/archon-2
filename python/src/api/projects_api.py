"""
Projects API endpoints for Archon

Handles:
- Project management (CRUD operations)
- Task management with hierarchical structure
- Streaming project creation with DocumentAgent integration
- WebSocket progress updates for project creation
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Set
import asyncio
import secrets
from datetime import datetime, timedelta
import json
import uuid
import time

from ..utils import get_supabase_client
import logging
from ..logfire_config import get_logger

# Get logfire logger for this module - use logfire directly like MCP server does
from ..logfire_config import logfire
logfire_logger = logfire

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["projects"])

class CreateProjectRequest(BaseModel):
    title: str
    description: Optional[str] = None
    github_repo: Optional[str] = None
    color: Optional[str] = 'blue'
    icon: Optional[str] = 'Briefcase'
    prd: Optional[Dict[str, Any]] = None
    docs: Optional[List[Any]] = None
    features: Optional[List[Any]] = None
    data: Optional[List[Any]] = None
    technical_sources: Optional[List[str]] = None  # List of knowledge source IDs
    business_sources: Optional[List[str]] = None   # List of knowledge source IDs
    pinned: Optional[bool] = None  # Whether this project should be pinned to top

class UpdateProjectRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None  # Add description field
    github_repo: Optional[str] = None
    prd: Optional[Dict[str, Any]] = None
    docs: Optional[List[Any]] = None
    features: Optional[List[Any]] = None
    data: Optional[List[Any]] = None
    technical_sources: Optional[List[str]] = None  # List of knowledge source IDs
    business_sources: Optional[List[str]] = None   # List of knowledge source IDs
    pinned: Optional[bool] = None  # Whether this project is pinned to top

class CreateTaskRequest(BaseModel):
    project_id: str
    parent_task_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: Optional[str] = 'todo'
    assignee: Optional[str] = 'User'
    task_order: Optional[int] = 0
    feature: Optional[str] = None

class ProjectCreationProgressData(BaseModel):
    progressId: str
    status: str
    percentage: int
    step: Optional[str] = None
    currentStep: Optional[str] = None
    eta: Optional[str] = None
    error: Optional[str] = None
    logs: List[str] = []
    project: Optional[Dict[str, Any]] = None
    duration: Optional[str] = None

class ProjectCreationProgressManager:
    """Manages project creation progress tracking and WebSocket streaming."""
    
    def __init__(self):
        self.active_creations: Dict[str, Dict[str, Any]] = {}
        self.progress_websockets: Dict[str, List[WebSocket]] = {}
    
    def start_creation(self, progress_id: str, initial_data: Dict[str, Any]) -> None:
        """Start tracking a new project creation operation."""
        self.active_creations[progress_id] = {
            'status': 'starting',
            'percentage': 0,
            'start_time': datetime.now(),
            'logs': ['🚀 Starting project creation...'],
            'step': 'initialization',
            **initial_data
        }
        
    async def update_progress(self, progress_id: str, update_data: Dict[str, Any]) -> None:
        """Update creation progress and notify connected clients."""
        if progress_id not in self.active_creations:
            return
        
        # Update progress data
        self.active_creations[progress_id].update(update_data)
        
        # Add log if provided
        if 'log' in update_data:
            self.active_creations[progress_id]['logs'].append(update_data['log'])
            # Keep only last 50 logs
            if len(self.active_creations[progress_id]['logs']) > 50:
                self.active_creations[progress_id]['logs'] = self.active_creations[progress_id]['logs'][-50:]
        
        # Broadcast to connected WebSocket clients
        await self._broadcast_progress(progress_id)
    
    async def complete_creation(self, progress_id: str, completion_data: Dict[str, Any]) -> None:
        """Mark a project creation as completed and send final update."""
        if progress_id not in self.active_creations:
            return
        
        completion_data.update({
            'status': 'completed',
            'percentage': 100,
            'step': 'finished',
            'log': '✅ Project creation completed successfully!',
            'duration': str(datetime.now() - self.active_creations[progress_id]['start_time'])
        })
        
        self.active_creations[progress_id].update(completion_data)
        await self._broadcast_progress(progress_id)
        
        # Clean up after a delay
        await asyncio.sleep(5)
        if progress_id in self.active_creations:
            del self.active_creations[progress_id]
    
    async def error_creation(self, progress_id: str, error_message: str) -> None:
        """Mark a project creation as failed and send error update."""
        if progress_id not in self.active_creations:
            return
        
        self.active_creations[progress_id].update({
            'status': 'error',
            'error': error_message,
            'log': f'❌ Error: {error_message}',
            'step': 'failed'
        })
        
        await self._broadcast_progress(progress_id)
    
    async def add_websocket(self, progress_id: str, websocket: WebSocket) -> None:
        """Add a WebSocket connection for progress updates."""
        await websocket.accept()
        
        if progress_id not in self.progress_websockets:
            self.progress_websockets[progress_id] = []
        
        self.progress_websockets[progress_id].append(websocket)
        
        # Send current progress if available
        if progress_id in self.active_creations:
            try:
                data = self.active_creations[progress_id].copy()
                data['progressId'] = progress_id
                
                if 'start_time' in data and hasattr(data['start_time'], 'isoformat'):
                    data['start_time'] = data['start_time'].isoformat()
                
                message = {
                    "type": "project_progress",
                    "data": data
                }
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error sending initial project creation progress: {e}")
        else:
            try:
                await websocket.send_json({
                    "type": "connection_established",
                    "data": {"progressId": progress_id, "status": "waiting"}
                })
            except Exception as e:
                print(f"Error sending project creation connection confirmation: {e}")
    
    def remove_websocket(self, progress_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if progress_id in self.progress_websockets:
            try:
                self.progress_websockets[progress_id].remove(websocket)
                if not self.progress_websockets[progress_id]:
                    del self.progress_websockets[progress_id]
            except ValueError:
                pass
    
    async def _broadcast_progress(self, progress_id: str) -> None:
        """Broadcast progress update to all connected clients."""
        if progress_id not in self.progress_websockets:
            return
        
        progress_data = self.active_creations.get(progress_id, {}).copy()
        progress_data['progressId'] = progress_id
        
        if 'start_time' in progress_data and hasattr(progress_data['start_time'], 'isoformat'):
            progress_data['start_time'] = progress_data['start_time'].isoformat()
        
        message = {
            "type": "project_progress",
            "data": progress_data
        }
        
        if progress_data.get('status') == 'completed':
            message["type"] = "project_completed"
        elif progress_data.get('status') == 'error':
            message["type"] = "project_error"
        
        # Send to all connected WebSocket clients
        disconnected = []
        for websocket in self.progress_websockets[progress_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)
        
        # Clean up disconnected WebSockets
        for ws in disconnected:
            self.remove_websocket(progress_id, ws)

# Global project creation progress manager
project_creation_manager = ProjectCreationProgressManager()

# WebSocket Connection Manager for Task Updates
class TaskUpdateManager:
    """
    Manages WebSocket connections for task updates with session-based isolation.
    Allows multiple chat sessions per project with independent WebSocket connections.
    """
    def __init__(self):
        # Changed to nested structure: project_id -> session_id -> websockets
        self.session_connections: Dict[str, Dict[str, List[WebSocket]]] = {}

    async def connect_to_session(self, websocket: WebSocket, project_id: str, session_id: str):
        """Connect a WebSocket to receive updates for a specific project session"""
        with logfire_logger.span("task_websocket_connect") as span:
            span.set_attribute("project_id", project_id)
            span.set_attribute("session_id", session_id)
            
            try:
                # WebSocket is already accepted in the endpoint, don't accept again
                logfire_logger.info("Task WebSocket connected", project_id=project_id, session_id=session_id)
                
                # Initialize nested structure if needed
                if project_id not in self.session_connections:
                    self.session_connections[project_id] = {}
                
                if session_id not in self.session_connections[project_id]:
                    self.session_connections[project_id][session_id] = []
                
                self.session_connections[project_id][session_id].append(websocket)
                span.set_attribute("success", True)
                span.set_attribute("total_sessions", len(self.session_connections[project_id]))
                span.set_attribute("session_connections", len(self.session_connections[project_id][session_id]))
                
            except Exception as e:
                logfire_logger.error("Failed to connect task WebSocket", project_id=project_id, session_id=session_id, error=str(e))
                span.set_attribute("success", False)
                span.set_attribute("error", str(e))
                raise
    
    def disconnect_from_session(self, websocket: WebSocket, project_id: str, session_id: str):
        """Disconnect a WebSocket from project session task updates"""
        if (project_id in self.session_connections and 
            session_id in self.session_connections[project_id]):
            try:
                self.session_connections[project_id][session_id].remove(websocket)
                
                # Clean up empty structures
                if not self.session_connections[project_id][session_id]:
                    del self.session_connections[project_id][session_id]
                    
                if not self.session_connections[project_id]:
                    del self.session_connections[project_id]
                    
                logfire_logger.info("Task WebSocket disconnected", project_id=project_id, session_id=session_id)
            except ValueError:
                pass  # WebSocket not in list

    async def broadcast_task_update(self, project_id: str, event_type: str, task_data: Dict[str, Any], target_session_id: str = None):
        """Broadcast a task update to connected sessions for a project"""
        with logfire_logger.span("task_websocket_broadcast") as span:
            span.set_attribute("project_id", project_id)
            span.set_attribute("event_type", event_type)
            span.set_attribute("task_id", task_data.get("id"))
            span.set_attribute("target_session_id", target_session_id)
            
            if project_id not in self.session_connections:
                span.set_attribute("sessions", 0)
                return
            
            successful_broadcasts = 0
            total_connections = 0
            disconnected = []
            
            # Determine which sessions to broadcast to
            sessions_to_broadcast = {}
            if target_session_id and target_session_id in self.session_connections[project_id]:
                # Broadcast to specific session only
                sessions_to_broadcast[target_session_id] = self.session_connections[project_id][target_session_id]
            else:
                # Broadcast to all sessions for this project
                sessions_to_broadcast = self.session_connections[project_id].copy()
            
            for session_id, websockets in sessions_to_broadcast.items():
                connections = websockets[:]
                total_connections += len(connections)
                
                message = {
                    "type": event_type,
                    "data": task_data,
                    "timestamp": datetime.now().isoformat(),
                    "project_id": project_id,
                    "session_id": session_id
                }
                
                for websocket in connections:
                    try:
                        # Check if WebSocket is still open before sending
                        if websocket.client_state.name == "CONNECTED":
                            await websocket.send_json(message)
                            successful_broadcasts += 1
                        else:
                            disconnected.append((websocket, project_id, session_id))
                    except Exception as e:
                        # Only log as warning if it's not a normal connection close
                        if "ConnectionClosed" not in str(e) and "close" not in str(e).lower():
                            logfire_logger.warning("Failed to send task update to WebSocket", error=str(e), session_id=session_id)
                        else:
                            logfire_logger.debug("WebSocket connection closed normally", error=str(e), session_id=session_id)
                        disconnected.append((websocket, project_id, session_id))
            
            # Remove disconnected WebSockets
            for ws, proj_id, sess_id in disconnected:
                self.disconnect_from_session(ws, proj_id, sess_id)
            
            logfire_logger.info("Task update broadcasted", 
                          project_id=project_id, 
                          event_type=event_type,
                          successful_broadcasts=successful_broadcasts,
                          failed_broadcasts=len(disconnected),
                          total_sessions=len(sessions_to_broadcast),
                          total_connections=total_connections)
            
            span.set_attribute("successful_broadcasts", successful_broadcasts)
            span.set_attribute("failed_broadcasts", len(disconnected))
            span.set_attribute("total_sessions", len(sessions_to_broadcast))
            span.set_attribute("total_connections", total_connections)

# Global task update manager
task_update_manager = TaskUpdateManager()

# Database Change Detection System for MCP-WebSocket Bridge
class DatabaseChangeDetector:
    """
    Monitors database changes and broadcasts WebSocket updates.
    This bridges MCP server operations with real-time WebSocket notifications
    while maintaining separation of concerns.
    """
    
    def __init__(self):
        self.last_check_times: Dict[str, datetime] = {}
        self.polling_tasks: Dict[str, asyncio.Task] = {}
        self.check_interval = 15  # Increased from 5 to 15 seconds to reduce database load
        self.websocket_connections: Dict[str, List[Dict[str, Any]]] = {}
        self.content_hashes: Dict[str, str] = {}  # Track content changes
        self.last_db_query_time = 0  # Add global rate limiting
        self.min_query_interval = 2  # Minimum 2 seconds between any database queries
    
    def start_monitoring(self, project_id: str):
        """Start monitoring database changes for a project"""
        if project_id in self.polling_tasks:
            return  # Already monitoring
        
        self.last_check_times[project_id] = datetime.now()
        
        async def monitor_loop():
            while project_id in self.websocket_connections and self.websocket_connections[project_id]:
                try:
                    # Add global rate limiting to prevent database spam
                    current_time = time.time()
                    time_since_last_query = current_time - self.last_db_query_time
                    if time_since_last_query < self.min_query_interval:
                        sleep_time = self.min_query_interval - time_since_last_query
                        await asyncio.sleep(sleep_time)
                    
                    await self._check_and_broadcast_changes(project_id)
                    self.last_db_query_time = time.time()
                    
                    await asyncio.sleep(self.check_interval)
                except Exception as e:
                    logger.error(f"Error monitoring project {project_id}: {e}")
                    # On error, wait longer before retrying to prevent spam
                    await asyncio.sleep(self.check_interval * 2)
        
        # Store the monitoring task
        self.polling_tasks[project_id] = asyncio.create_task(monitor_loop())
        logger.info(f"Started monitoring database changes for project {project_id}")
    
    def stop_monitoring(self, project_id: str):
        """Stop monitoring database changes for a project"""
        if project_id in self.polling_tasks:
            self.polling_tasks[project_id].cancel()
            del self.polling_tasks[project_id]
        if project_id in self.last_check_times:
            del self.last_check_times[project_id]
        if project_id in self.content_hashes:
            del self.content_hashes[project_id]
        logger.info(f"Stopped monitoring database changes for project {project_id}")
    
    async def add_websocket_connection(self, project_id: str, websocket: WebSocket, session_id: str = None):
        """Add WebSocket connection and start monitoring if first connection for project"""
        if project_id not in self.websocket_connections:
            self.websocket_connections[project_id] = []
        
        # Store websocket with session context  
        connection_info = {
            "websocket": websocket,
            "session_id": session_id or str(uuid.uuid4()),
            "connected_at": datetime.now()
        }
        self.websocket_connections[project_id].append(connection_info)
        
        # Start monitoring this project if first connection
        if len(self.websocket_connections[project_id]) == 1:
            self.start_monitoring(project_id)
    
    def remove_websocket_connection(self, project_id: str, websocket: WebSocket, session_id: str = None):
        """Remove WebSocket connection and stop monitoring if no connections left"""
        if project_id in self.websocket_connections:
            # Remove the specific websocket connection
            self.websocket_connections[project_id] = [
                conn for conn in self.websocket_connections[project_id] 
                if conn["websocket"] != websocket
            ]
            
            if not self.websocket_connections[project_id]:
                # No more connections, stop monitoring
                del self.websocket_connections[project_id]
                self.stop_monitoring(project_id)
    
    async def _check_and_broadcast_changes(self, project_id: str):
        """Check for database changes and broadcast via WebSocket"""
        last_check = self.last_check_times.get(project_id)
        if not last_check:
            return
        
        try:
            supabase_client = get_supabase_client()
            
            # Query for tasks updated since last check
            response = supabase_client.table("tasks").select("*").eq("project_id", project_id).gte("updated_at", last_check.isoformat()).execute()
            
            changed_tasks = response.data if response.data else []
            
            if changed_tasks:
                # Update last check time
                self.last_check_times[project_id] = datetime.now()
                
                # Check for actual content changes using hashes
                actual_changes = []
                for task in changed_tasks:
                    task_hash = hash(str(sorted(task.items())))
                    old_hash = self.content_hashes.get(f"{project_id}:{task['id']}")
                    
                    if old_hash != task_hash:
                        self.content_hashes[f"{project_id}:{task['id']}"] = task_hash
                        actual_changes.append(task)
                
                if actual_changes:
                    # Broadcast changes to all connected WebSockets
                    await self._broadcast_to_project(project_id, {
                        "type": "tasks_updated",
                        "data": {
                            "project_id": project_id,
                            "updated_tasks": actual_changes,
                            "timestamp": datetime.now().isoformat()
                        }
                    })
                    logger.info(f"Broadcast {len(actual_changes)} task changes for project {project_id}")
            else:
                # No changes found, just update the check time
                self.last_check_times[project_id] = datetime.now()
        
        except Exception as e:
            logger.error(f"Error checking database changes for project {project_id}: {e}")
    
    async def _broadcast_to_project(self, project_id: str, message: dict):
        """Broadcast message to all WebSocket connections for a project"""
        if project_id not in self.websocket_connections:
            return
        
        disconnected = []
        for conn in self.websocket_connections[project_id]:
            websocket = conn["websocket"]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.append(conn)
        
        # Clean up disconnected WebSockets
        for conn in disconnected:
            self.remove_websocket_connection(project_id, conn["websocket"], conn["session_id"])

# Global database change detector
db_change_detector = DatabaseChangeDetector()

# Connection Manager for Project List WebSocket
class ProjectListConnectionManager:
    """Manages WebSocket connections for real-time project list updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket for project list updates."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logfire_logger.info("Project list WebSocket connected", total_connections=len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket from project list updates."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logfire_logger.info("Project list WebSocket disconnected", total_connections=len(self.active_connections))
    
    async def send_project_list(self, websocket: WebSocket):
        """Send current project list to a specific WebSocket connection."""
        try:
            # Get current projects using the same logic as list_projects endpoint
            supabase_client = get_supabase_client()
            response = supabase_client.table("projects").select("*").order("created_at", desc=True).execute()
            
            projects = []
            for project in response.data:
                # Get linked sources for this project
                technical_sources = []
                business_sources = []
                
                try:
                    sources_response = supabase_client.table("project_sources").select("source_id, notes").eq("project_id", project["id"]).execute()
                    for source_link in sources_response.data:
                        if source_link.get("notes") == "technical":
                            technical_sources.append(source_link["source_id"])
                        elif source_link.get("notes") == "business":
                            business_sources.append(source_link["source_id"])
                except Exception as e:
                    logger.warning(f"Failed to retrieve linked sources for project {project['id']}: {e}")
                
                projects.append({
                    "id": project["id"],
                    "title": project["title"],
                    "github_repo": project.get("github_repo"),
                    "created_at": project["created_at"],
                    "updated_at": project["updated_at"],
                    "prd": project.get("prd", {}),
                    "docs": project.get("docs", []),
                    "features": project.get("features", []),
                    "data": project.get("data", []),
                    "technical_sources": technical_sources,
                    "business_sources": business_sources,
                    "pinned": project.get("pinned", False)
                })
            
            # Send projects update message matching knowledge base pattern
            await websocket.send_json({
                "type": "projects_update",
                "data": {
                    "projects": projects,
                    "total": len(projects)
                }
            })
            
        except Exception as e:
            logfire_logger.error("Failed to send project list via WebSocket", error=str(e))
    
    async def broadcast_project_update(self):
        """Broadcast project list update to all connected clients."""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await self.send_project_list(connection)
            except Exception as e:
                logfire_logger.warning("Failed to send project update to WebSocket", error=str(e))
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

# Global project list connection manager
project_list_manager = ProjectListConnectionManager()

@router.get("/projects")
async def list_projects():
    """List all projects."""
    with logfire_logger.span("api_list_projects") as span:
        span.set_attribute("endpoint", "/api/projects")
        span.set_attribute("method", "GET")
        
        try:
            logfire_logger.info("Listing all projects")
            supabase_client = get_supabase_client()
            
            response = supabase_client.table("projects").select("*").order("created_at", desc=True).execute()
            
            projects = []
            for project in response.data:
                # Get linked sources for this project
                technical_sources = []
                business_sources = []
                
                try:
                    sources_response = supabase_client.table("project_sources").select("source_id, notes").eq("project_id", project["id"]).execute()
                    for source_link in sources_response.data:
                        if source_link.get("notes") == "technical":
                            technical_sources.append(source_link["source_id"])
                        elif source_link.get("notes") == "business":
                            business_sources.append(source_link["source_id"])
                except Exception as e:
                    logger.warning(f"Failed to retrieve linked sources for project {project['id']}: {e}")
                
                projects.append({
                    "id": project["id"],
                    "title": project["title"],
                    "description": project.get("description", ""),  # Include description field
                    "github_repo": project.get("github_repo"),
                    "created_at": project["created_at"],
                    "updated_at": project["updated_at"],
                    "prd": project.get("prd", {}),
                    "docs": project.get("docs", []),
                    "features": project.get("features", []),
                    "data": project.get("data", []),
                    "technical_sources": technical_sources,
                    "business_sources": business_sources,
                    "pinned": project.get("pinned", False)  # Include pinned field with default False
                })
            
            logfire_logger.info("Projects listed successfully", count=len(projects))
            span.set_attribute("project_count", len(projects))
            
            return projects
            
        except Exception as e:
            logfire_logger.error("Failed to list projects", error=str(e))
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail={'error': str(e)})

@router.post("/projects")
async def create_project(request: CreateProjectRequest):
    """Create a new project with streaming progress."""
    with logfire_logger.span("api_create_project") as span:
        span.set_attribute("endpoint", "/api/projects")
        span.set_attribute("method", "POST")
        span.set_attribute("title", request.title)
        span.set_attribute("has_github_repo", request.github_repo is not None)
        span.set_attribute("has_technical_sources", request.technical_sources is not None)
        span.set_attribute("has_business_sources", request.business_sources is not None)
        
        try:
            logfire_logger.info("Creating new project", title=request.title, github_repo=request.github_repo)
            
            # Generate unique progress ID for this creation
            progress_id = secrets.token_hex(16)
            span.set_attribute("progress_id", progress_id)
            
            # Start tracking creation progress
            project_creation_manager.start_creation(progress_id, {
                'title': request.title,
                'description': request.description or '',
                'github_repo': request.github_repo
            })
            
            # Start background task to actually create the project
            asyncio.create_task(_create_project_background(progress_id, request))
            
            logfire_logger.info("Project creation started", progress_id=progress_id, title=request.title)
            span.set_attribute("success", True)
            
            # Return progress_id immediately so frontend can connect to WebSocket
            return {
                "progress_id": progress_id,
                "status": "started",
                "message": "Project creation started. Connect to WebSocket for progress updates."
            }
            
        except Exception as e:
            logfire_logger.error("Failed to start project creation", error=str(e), title=request.title)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail={'error': str(e)})

async def _create_project_background(progress_id: str, request: CreateProjectRequest):
    """Background task to create project with AI assistance."""
    supabase = get_supabase_client()
    
    try:
        # Create basic project structure first
        await project_creation_manager.update_progress(progress_id, {
            'percentage': 30,
            'step': 'database_setup',
            'log': '🗄️ Setting up project database...'
        })
        
        # Create the basic project record in database first
        project_data = {
            'title': request.title,
            'description': request.description or "",
            'github_repo': request.github_repo,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'docs': [],  # Empty docs array to start
            'features': {},
            'data': {}
        }
        
        # Create the project in database
        response = supabase.table('projects').insert(project_data).execute()
        if not response.data:
            raise Exception("Failed to create project in database")
        
        project_id = response.data[0]['id']
        
        await project_creation_manager.update_progress(progress_id, {
            'percentage': 50,
            'step': 'processing_requirements',
            'log': '🧠 AI is analyzing project requirements...'
        })
        
        # Only initialize DocumentAgent if we have an OpenAI API key
        try:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            
            if api_key:
                # Import DocumentAgent (lazy import to avoid startup issues)
                from ..agents.document_agent import DocumentAgent
                
                await project_creation_manager.update_progress(progress_id, {
                    'percentage': 70,
                    'step': 'ai_generation',
                    'log': '✨ AI is creating project documentation...'
                })
                
                # Initialize DocumentAgent
                document_agent = DocumentAgent()
                
                # Generate comprehensive PRD using conversation
                prd_request = f"Create a PRD document titled '{request.title} - Product Requirements Document' for a project called '{request.title}'"
                if request.description:
                    prd_request += f" with the following description: {request.description}"
                if request.github_repo:
                    prd_request += f" (GitHub repo: {request.github_repo})"
                
                # Create a progress callback for the document agent
                async def agent_progress_callback(update_data):
                    await project_creation_manager.update_progress(progress_id, update_data)
                
                # Run the document agent to create PRD with the real project ID
                agent_result = await document_agent.run_conversation(
                    user_message=prd_request,
                    project_id=project_id,  # Use the real project ID
                    user_id="system",
                    progress_callback=agent_progress_callback
                )
                
                if agent_result.success:
                    await project_creation_manager.update_progress(progress_id, {
                        'percentage': 85,
                        'step': 'finalizing',
                        'log': f'📝 Successfully created project documentation'
                    })
                else:
                    await project_creation_manager.update_progress(progress_id, {
                        'percentage': 85,
                        'step': 'finalizing',
                        'log': f'⚠️ Project created but AI documentation generation had issues: {agent_result.message}'
                    })
            else:
                await project_creation_manager.update_progress(progress_id, {
                    'percentage': 85,
                    'step': 'finalizing',
                    'log': '⚠️ OpenAI API key not configured - skipping AI documentation generation'
                })
                
        except Exception as ai_error:
            logger.warning(f"AI generation failed, continuing with basic project: {ai_error}")
            await project_creation_manager.update_progress(progress_id, {
                'percentage': 85,
                'step': 'finalizing',
                'log': f'⚠️ AI generation failed - created basic project structure'
            })
        
        # Final success - fetch the complete project data to send to frontend
        final_project_response = supabase.table('projects').select('*').eq('id', project_id).execute()
        if final_project_response.data:
            final_project = final_project_response.data[0]
            # Include the pinned field (default to False if not present)
            project_data_for_frontend = {
                'id': final_project['id'],
                'title': final_project['title'],
                'description': final_project.get('description', ''),
                'github_repo': final_project.get('github_repo'),
                'created_at': final_project['created_at'],
                'updated_at': final_project['updated_at'],
                'prd': final_project.get('prd', {}),
                'docs': final_project.get('docs', []),
                'features': final_project.get('features', []),
                'data': final_project.get('data', []),
                'pinned': final_project.get('pinned', False),  # Include pinned field
                'color': request.color or 'blue',
                'icon': request.icon or 'Briefcase',
                'technical_sources': [],  # Empty initially
                'business_sources': []     # Empty initially
            }
            
            await project_creation_manager.update_progress(progress_id, {
                'percentage': 100,
                'step': 'completed',
                'log': f'🎉 Project "{request.title}" created successfully!',
                'project_id': project_id,
                'project': project_data_for_frontend  # Send full project object
            })
        else:
            # Fallback if we can't fetch the project
            await project_creation_manager.update_progress(progress_id, {
                'percentage': 100,
                'step': 'completed',
                'log': f'🎉 Project "{request.title}" created successfully!',
                'project_id': project_id
            })
        
        # Broadcast project list update to WebSocket clients
        await project_list_manager.broadcast_project_update()
        
    except Exception as e:
        logger.error(f"Project creation failed: {str(e)}")
        await project_creation_manager.update_progress(progress_id, {
            'percentage': 0,
            'step': 'failed',
            'log': f'❌ Project creation failed: {str(e)}'
        })
        raise

@router.get("/projects/health")
async def projects_health():
    """Health check for projects API and database schema validation."""
    with logfire_logger.span("api_projects_health") as span:
        span.set_attribute("endpoint", "/api/projects/health")
        span.set_attribute("method", "GET")
        
        try:
            logfire_logger.info("Projects health check requested")
            supabase_client = get_supabase_client()
            
            # Check if projects table exists by trying a simple query
            try:
                response = supabase_client.table("projects").select("id").limit(1).execute()
                projects_table_exists = True
                logfire_logger.info("Projects table detected successfully")
            except Exception as e:
                projects_table_exists = False
                logfire_logger.warning("Projects table not found", error=str(e))
            
            # Check if tasks table exists
            try:
                response = supabase_client.table("tasks").select("id").limit(1).execute()
                tasks_table_exists = True
                logfire_logger.info("Tasks table detected successfully")
            except Exception as e:
                tasks_table_exists = False
                logfire_logger.warning("Tasks table not found", error=str(e))
            
            schema_valid = projects_table_exists and tasks_table_exists
            
            result = {
                "status": "healthy" if schema_valid else "schema_missing",
                "service": "projects",
                "schema": {
                    "projects_table": projects_table_exists,
                    "tasks_table": tasks_table_exists,
                    "valid": schema_valid
                }
            }
            
            span.set_attribute("status", result["status"])
            span.set_attribute("schema_valid", schema_valid)
            
            logfire_logger.info("Projects health check completed", 
                        status=result["status"], 
                        schema_valid=schema_valid)
            
            return result
            
        except Exception as e:
            logfire_logger.error("Projects health check failed", error=str(e))
            span.set_attribute("error", str(e))
            return {
                "status": "error",
                "service": "projects",
                "error": str(e),
                "schema": {
                    "projects_table": False,
                    "tasks_table": False,
                    "valid": False
                }
            }

@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific project."""
    with logfire_logger.span("api_get_project") as span:
        span.set_attribute("endpoint", f"/api/projects/{project_id}")
        span.set_attribute("method", "GET")
        span.set_attribute("project_id", project_id)
        
        try:
            logfire_logger.info("Getting project", project_id=project_id)
            supabase_client = get_supabase_client()
            
            response = supabase_client.table("projects").select("*").eq("id", project_id).execute()
            
            if response.data:
                project = response.data[0]
                
                # Get linked sources
                technical_sources = []
                business_sources = []
                
                try:
                    # Get source IDs from project_sources table
                    sources_response = supabase_client.table("project_sources").select("source_id, notes").eq("project_id", project["id"]).execute()
                    
                    # Collect source IDs by type
                    technical_source_ids = []
                    business_source_ids = []
                    
                    for source_link in sources_response.data:
                        if source_link.get("notes") == "technical":
                            technical_source_ids.append(source_link["source_id"])
                        elif source_link.get("notes") == "business":
                            business_source_ids.append(source_link["source_id"])
                    
                    # Fetch full source objects from sources table
                    if technical_source_ids:
                        tech_sources_response = supabase_client.table("sources").select("*").in_("source_id", technical_source_ids).execute()
                        technical_sources = tech_sources_response.data
                    
                    if business_source_ids:
                        biz_sources_response = supabase_client.table("sources").select("*").in_("source_id", business_source_ids).execute()
                        business_sources = biz_sources_response.data
                        
                except Exception as e:
                    logger.warning(f"Failed to retrieve linked sources for project {project['id']}: {e}")
                
                logfire_logger.info("Project retrieved successfully", project_id=project_id, title=project["title"])
                span.set_attribute("success", True)
                span.set_attribute("title", project["title"])
                
                return {
                    "id": project["id"],
                    "title": project["title"],
                    "description": project.get("description", ""),  # Include description field
                    "github_repo": project.get("github_repo"),
                    "created_at": project["created_at"],
                    "updated_at": project["updated_at"],
                    "prd": project.get("prd", {}),
                    "docs": project.get("docs", []),
                    "features": project.get("features", []),
                    "data": project.get("data", []),
                    "technical_sources": technical_sources,
                    "business_sources": business_sources,
                    "pinned": project.get("pinned", False)  # Include pinned field with default False
                }
            else:
                logfire_logger.warning("Project not found", project_id=project_id)
                span.set_attribute("found", False)
                raise HTTPException(status_code=404, detail={'error': f'Project with ID {project_id} not found'})
                    
        except HTTPException:
            raise
        except Exception as e:
            logfire_logger.error("Failed to get project", error=str(e), project_id=project_id)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail={'error': str(e)})

@router.put("/projects/{project_id}")
async def update_project(project_id: str, request: UpdateProjectRequest):
    """Update a project with comprehensive Logfire monitoring."""
    with logfire_logger.span("api_update_project") as span:
        span.set_attribute("endpoint", f"/projects/{project_id}")
        span.set_attribute("method", "PUT")
        span.set_attribute("project_id", project_id)
        span.set_attribute("has_technical_sources", request.technical_sources is not None)
        span.set_attribute("has_business_sources", request.business_sources is not None)
        
        if request.technical_sources is not None:
            span.set_attribute("technical_sources_count", len(request.technical_sources))
        if request.business_sources is not None:
            span.set_attribute("business_sources_count", len(request.business_sources))
        
        try:
            supabase_client = get_supabase_client()
            
            # Build update data with monitoring
            with logfire_logger.span("prepare_update_data") as prep_span:
                update_data = {"updated_at": datetime.now().isoformat()}
                
                if request.title is not None:
                    update_data["title"] = request.title
                if request.description is not None:
                    update_data["description"] = request.description
                if request.github_repo is not None:
                    update_data["github_repo"] = request.github_repo
                if request.prd is not None:
                    update_data["prd"] = request.prd
                if request.docs is not None:
                    update_data["docs"] = request.docs
                if request.features is not None:
                    update_data["features"] = request.features
                if request.data is not None:
                    update_data["data"] = request.data
                
                # Handle pinned field and ensure only one project can be pinned at a time
                if request.pinned is not None:
                    update_data["pinned"] = request.pinned
                    
                    # If pinning this project, unpin all others
                    if request.pinned:
                        with logfire_logger.span("unpin_other_projects") as unpin_span:
                            try:
                                # Unpin all other projects
                                supabase_client.table("projects").update({"pinned": False}).neq("id", project_id).eq("pinned", True).execute()
                                unpin_span.set_attribute("success", True)
                            except Exception as e:
                                unpin_span.set_attribute("success", False)
                                unpin_span.set_attribute("error", str(e))
                                logger.warning(f"Failed to unpin other projects: {e}")
                                # Continue with this project's update regardless
                
                prep_span.set_attribute("update_fields_count", len(update_data) - 1)  # -1 for updated_at
            
            # Create version snapshots for JSONB fields before updating
            # Check if versioning is available by trying to import the service
            try:
                from ..services.projects.versioning_service import VersioningService
                VERSIONING_AVAILABLE = True
            except ImportError:
                VERSIONING_AVAILABLE = False
                
            if VERSIONING_AVAILABLE:
                with logfire_logger.span("create_version_snapshots") as version_span:
                    version_count = 0
                    try:
                        # Get current project data for comparison
                        current_project_response = supabase_client.table("projects").select("*").eq("id", project_id).execute()
                        if current_project_response.data:
                            current_project = current_project_response.data[0]
                            
                            # Create versions for updated JSONB fields
                            for field_name in ['docs', 'prd', 'features', 'data']:
                                if getattr(request, field_name, None) is not None:
                                    current_content = current_project.get(field_name, {})
                                    new_content = getattr(request, field_name)
                                    
                                    # Only create version if content actually changed
                                    if current_content != new_content:
                                        # Create version snapshot using versioning service
                                        versioning_service = VersioningService(supabase_client)
                                        success, result = versioning_service.create_version(
                                            project_id=project_id,
                                            field_name=field_name,
                                            content=current_content,
                                            change_summary=f"Updated {field_name} via API",
                                            change_type="update",
                                            created_by="api_user"
                                        )
                                        if success:
                                            version_count += 1
                                        
                        version_span.set_attribute("versions_created", version_count)
                        logfire_logger.info(f"Created {version_count} version snapshots before update")
                        
                    except Exception as e:
                        version_span.set_attribute("error", str(e))
                        logger.warning(f"Failed to create version snapshots: {e}")
                        # Don't fail the update, just log the warning
            
            # Update project in database with monitoring
            with logfire_logger.span("update_project_record") as update_span:
                response = supabase_client.table("projects").update(update_data).eq("id", project_id).execute()
                
                if not response.data:
                    update_span.set_attribute("success", False)
                    raise HTTPException(status_code=404, detail={'error': f'Project with ID {project_id} not found'})
                
                project = response.data[0]
                update_span.set_attribute("success", True)
            
            # Handle technical_sources with monitoring
            if request.technical_sources is not None:
                with logfire_logger.span("update_technical_sources") as tech_span:
                    tech_span.set_attribute("source_count", len(request.technical_sources))
                    
                    # Remove existing technical sources
                    supabase_client.table("project_sources").delete().eq("project_id", project_id).eq("notes", "technical").execute()
                    
                    # Add new technical sources
                    successful_links = 0
                    failed_links = 0
                    
                    for source_id in request.technical_sources:
                        try:
                            supabase_client.table("project_sources").insert({
                                "project_id": project_id,
                                "source_id": source_id,
                                "notes": "technical"
                            }).execute()
                            successful_links += 1
                        except Exception as e:
                            failed_links += 1
                            logger.warning(f"Failed to link technical source {source_id}: {e}")
                            logfire_logger.warning(f"Technical source link failed", source_id=source_id, error=str(e))
                    
                    tech_span.set_attribute("successful_links", successful_links)
                    tech_span.set_attribute("failed_links", failed_links)
                    logfire_logger.info(f"Technical sources updated: {successful_links} success, {failed_links} failed")
            
            # Handle business_sources with monitoring
            if request.business_sources is not None:
                with logfire_logger.span("update_business_sources") as biz_span:
                    biz_span.set_attribute("source_count", len(request.business_sources))
                    
                    # Remove existing business sources
                    supabase_client.table("project_sources").delete().eq("project_id", project_id).eq("notes", "business").execute()
                    
                    # Add new business sources
                    successful_links = 0
                    failed_links = 0
                    
                    for source_id in request.business_sources:
                        try:
                            supabase_client.table("project_sources").insert({
                                "project_id": project_id,
                                "source_id": source_id,
                                "notes": "business"
                            }).execute()
                            successful_links += 1
                        except Exception as e:
                            failed_links += 1
                            logger.warning(f"Failed to link business source {source_id}: {e}")
                            logfire_logger.warning(f"Business source link failed", source_id=source_id, error=str(e))
                    
                    biz_span.set_attribute("successful_links", successful_links)
                    biz_span.set_attribute("failed_links", failed_links)
                    logfire_logger.info(f"Business sources updated: {successful_links} success, {failed_links} failed")
            
            # Get linked sources for response with monitoring
            technical_sources = []
            business_sources = []
            
            with logfire_logger.span("fetch_linked_sources_for_response") as fetch_span:
                try:
                    # Get source IDs from project_sources table
                    sources_response = supabase_client.table("project_sources").select("source_id, notes").eq("project_id", project_id).execute()
                    
                    # Collect source IDs by type
                    technical_source_ids = []
                    business_source_ids = []
                    
                    for source_link in sources_response.data:
                        if source_link.get("notes") == "technical":
                            technical_source_ids.append(source_link["source_id"])
                        elif source_link.get("notes") == "business":
                            business_source_ids.append(source_link["source_id"])
                    
                    fetch_span.set_attribute("technical_ids_found", len(technical_source_ids))
                    fetch_span.set_attribute("business_ids_found", len(business_source_ids))
                    
                    # Fetch full source objects from sources table
                    if technical_source_ids:
                        tech_sources_response = supabase_client.table("sources").select("*").in_("source_id", technical_source_ids).execute()
                        technical_sources = tech_sources_response.data
                    
                    if business_source_ids:
                        biz_sources_response = supabase_client.table("sources").select("*").in_("source_id", business_source_ids).execute()
                        business_sources = biz_sources_response.data
                    
                    fetch_span.set_attribute("technical_objects_fetched", len(technical_sources))
                    fetch_span.set_attribute("business_objects_fetched", len(business_sources))
                        
                except Exception as e:
                    fetch_span.set_attribute("success", False)
                    fetch_span.set_attribute("error", str(e))
                    logger.warning(f"Failed to retrieve linked sources: {e}")
                    logfire_logger.warning(f"Failed to fetch linked sources for response", project_id=project_id, error=str(e))
            
            span.set_attribute("success", True)
            span.set_attribute("final_technical_sources", len(technical_sources))
            span.set_attribute("final_business_sources", len(business_sources))
            
            logfire_logger.info(f"Project updated successfully", 
                              project_id=project_id, 
                              technical_sources=len(technical_sources),
                              business_sources=len(business_sources))
            
            # Convert datetime objects to ISO strings before returning (critical for WebSocket serialization)
            created_at = project["created_at"]
            updated_at = project["updated_at"]
            
            # Ensure datetime objects are converted to strings
            if hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            if hasattr(updated_at, 'isoformat'):
                updated_at = updated_at.isoformat()
            
            # Broadcast project list update to WebSocket clients
            await project_list_manager.broadcast_project_update()
            
            return {
                "id": project["id"],
                "title": project["title"],
                "github_repo": project.get("github_repo"),
                "created_at": created_at,
                "updated_at": updated_at,
                "prd": project.get("prd", {}),
                "docs": project.get("docs", []),
                "features": project.get("features", []),
                "data": project.get("data", []),
                "technical_sources": technical_sources,
                "business_sources": business_sources,
                "pinned": project.get("pinned", False)  # Include pinned field with default False
            }
                
        except HTTPException:
            span.set_attribute("success", False)
            span.set_attribute("error", "HTTP Exception")
            raise
        except Exception as e:
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            logfire_logger.error(f"Project update failed", project_id=project_id, error=str(e))
            raise HTTPException(status_code=500, detail={'error': str(e)})

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all its tasks."""
    with logfire_logger.span("api_delete_project") as span:
        span.set_attribute("endpoint", f"/api/projects/{project_id}")
        span.set_attribute("method", "DELETE")
        span.set_attribute("project_id", project_id)
        
        try:
            logfire_logger.info("Deleting project", project_id=project_id)
            supabase_client = get_supabase_client()
            
            # Delete project (tasks will be cascade deleted due to foreign key)
            response = supabase_client.table("projects").delete().eq("id", project_id).execute()
            
            # Broadcast project list update to WebSocket clients
            await project_list_manager.broadcast_project_update()
            
            logfire_logger.info("Project deleted successfully", project_id=project_id)
            span.set_attribute("success", True)
            
            return {"message": "Project deleted successfully"}
            
        except Exception as e:
            logfire_logger.error("Failed to delete project", error=str(e), project_id=project_id)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail={'error': str(e)})

@router.get("/projects/{project_id}/features")
async def get_project_features(project_id: str):
    """Get features from a project's features JSONB field."""
    with logfire_logger.span("api_get_project_features") as span:
        span.set_attribute("endpoint", f"/api/projects/{project_id}/features")
        span.set_attribute("method", "GET")
        span.set_attribute("project_id", project_id)
        
        try:
            logfire_logger.info("Getting project features", project_id=project_id)
            supabase_client = get_supabase_client()
            
            response = supabase_client.table("projects").select("features").eq("id", project_id).single().execute()
            
            if not response.data:
                logfire_logger.warning("Project not found for features", project_id=project_id)
                span.set_attribute("found", False)
                raise HTTPException(status_code=404, detail={'error': 'Project not found'})
            
            features = response.data.get("features", [])
            
            # Extract feature labels for dropdown options
            feature_options = []
            for feature in features:
                if isinstance(feature, dict) and "data" in feature and "label" in feature["data"]:
                    feature_options.append({
                        "id": feature.get("id", ""),
                        "label": feature["data"]["label"],
                        "type": feature["data"].get("type", ""),
                        "feature_type": feature.get("type", "page")
                    })
            
            logfire_logger.info("Project features retrieved", project_id=project_id, feature_count=len(feature_options))
            span.set_attribute("feature_count", len(feature_options))
            
            return {
                "features": feature_options,
                "count": len(feature_options)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logfire_logger.error("Failed to get project features", error=str(e), project_id=project_id)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail={'error': str(e)})

@router.get("/projects/{project_id}/tasks")
async def list_project_tasks(project_id: str, include_archived: bool = False, include_subtasks: bool = False):
    """List all tasks for a specific project. By default, filters out archived tasks and subtasks."""
    with logfire_logger.span("api_list_project_tasks") as span:
        span.set_attribute("endpoint", f"/api/projects/{project_id}/tasks")
        span.set_attribute("method", "GET")
        span.set_attribute("project_id", project_id)
        span.set_attribute("include_archived", include_archived)
        span.set_attribute("include_subtasks", include_subtasks) # Add this attribute
        
        try:
            logfire_logger.info("Listing project tasks", project_id=project_id, include_archived=include_archived, include_subtasks=include_subtasks) # Add this attribute
            supabase_client = get_supabase_client()
            
            # Build query to optionally exclude archived tasks and subtasks
            query = supabase_client.table("tasks").select("*").eq("project_id", project_id)
            
            # Only include non-archived tasks by default (handle NULL as False for backwards compatibility)
            if not include_archived:
                query = query.or_("archived.is.null,archived.eq.false")
            
            # Only include parent tasks by default (exclude subtasks)
            if not include_subtasks:
                query = query.is_("parent_task_id", None)
            
            response = query.order("task_order", desc=False).order("created_at", desc=False).execute()
            
            logfire_logger.info("Project tasks retrieved", project_id=project_id, task_count=len(response.data))
            span.set_attribute("task_count", len(response.data))
            
            return response.data
            
        except Exception as e:
            logfire_logger.error("Failed to list project tasks", error=str(e), project_id=project_id)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail={'error': str(e)})

@router.post("/tasks")
async def create_task(request: CreateTaskRequest):
    """Create a new task with automatic reordering and real-time WebSocket broadcasting."""
    with logfire_logger.span("api_create_task") as span:
        span.set_attribute("endpoint", "/tasks")
        span.set_attribute("method", "POST")
        span.set_attribute("project_id", request.project_id)
        span.set_attribute("title", request.title)
        span.set_attribute("assignee", request.assignee)
        span.set_attribute("status", request.status)
        
        try:
            supabase_client = get_supabase_client()
            
            task_status = request.status or 'todo'
            task_order = request.task_order or 0
            
            # REORDERING LOGIC: If inserting at a specific position, increment existing tasks
            if task_order > 0:
                # Get all tasks in the same project and status with task_order >= new task's order
                existing_tasks_response = supabase_client.table("tasks").select("id, task_order").eq("project_id", request.project_id).eq("status", task_status).gte("task_order", task_order).execute()
                
                if existing_tasks_response.data:
                    logfire_logger.info(f"Reordering {len(existing_tasks_response.data)} existing tasks", 
                                      project_id=request.project_id, 
                                      status=task_status, 
                                      insert_position=task_order)
                    span.set_attribute("tasks_to_reorder", len(existing_tasks_response.data))
                    
                    # Increment task_order for all affected tasks
                    for existing_task in existing_tasks_response.data:
                        new_order = existing_task["task_order"] + 1
                        supabase_client.table("tasks").update({
                            "task_order": new_order,
                            "updated_at": datetime.now().isoformat()
                        }).eq("id", existing_task["id"]).execute()
                        
                        logfire_logger.debug("Reordered task", 
                                           task_id=existing_task["id"], 
                                           old_order=existing_task["task_order"], 
                                           new_order=new_order)
            
            # Create task data
            task_data = {
                "project_id": request.project_id,
                "title": request.title,
                "description": request.description,
                "status": task_status,
                "assignee": request.assignee or 'User',
                "task_order": task_order,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            if request.parent_task_id:
                task_data["parent_task_id"] = request.parent_task_id
            if request.feature:
                task_data["feature"] = request.feature
            
            # Insert task into database
            response = supabase_client.table("tasks").insert(task_data).execute()
            
            if response.data:
                created_task = response.data[0]
                logfire_logger.info("Task created successfully with automatic reordering", 
                                  task_id=created_task["id"], 
                                  project_id=request.project_id,
                                  task_order=task_order)
                span.set_attribute("success", True)
                span.set_attribute("task_id", created_task["id"])
                span.set_attribute("final_task_order", task_order)
                
                # Broadcast real-time update to connected clients
                await task_update_manager.broadcast_task_update(
                    project_id=request.project_id,
                    event_type="task_created",
                    task_data=created_task
                )
                
                return {"message": "Task created successfully", "task": created_task}
            else:
                raise HTTPException(status_code=500, detail="Failed to create task")
                
        except Exception as e:
            logfire_logger.error("Failed to create task", error=str(e), project_id=request.project_id)
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task by ID."""
    with logfire_logger.span("api_get_task") as span:
        span.set_attribute("endpoint", f"/tasks/{task_id}")
        span.set_attribute("method", "GET")
        span.set_attribute("task_id", task_id)
        
        try:
            supabase_client = get_supabase_client()
            
            # Get task by ID - handle backwards compatibility for archived field
            response = supabase_client.table("tasks").select("*").eq("id", task_id).or_("archived.is.null,archived.eq.false").execute()
            
            if not response.data:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
            task = response.data[0]
            span.set_attribute("project_id", task.get("project_id"))
            span.set_attribute("success", True)
            
            logfire_logger.info("Task retrieved successfully", 
                              task_id=task_id, 
                              project_id=task.get("project_id"))
            
            return task
            
        except HTTPException:
            raise
        except Exception as e:
            logfire_logger.error("Failed to get task", error=str(e), task_id=task_id)
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))

class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    task_order: Optional[int] = None
    feature: Optional[str] = None

@router.put("/tasks/{task_id}")
async def update_task(task_id: str, request: UpdateTaskRequest):
    """Update a task with real-time WebSocket broadcasting."""
    with logfire_logger.span("api_update_task") as span:
        span.set_attribute("endpoint", f"/tasks/{task_id}")
        span.set_attribute("method", "PUT")
        span.set_attribute("task_id", task_id)
        
        try:
            supabase_client = get_supabase_client()
            
            # First get the current task to get project_id for broadcasting
            current_task_response = supabase_client.table("tasks").select("*").eq("id", task_id).execute()
            if not current_task_response.data:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
            current_task = current_task_response.data[0]
            project_id = current_task["project_id"]
            span.set_attribute("project_id", project_id)
            
            # Build update data
            update_data = {"updated_at": datetime.now().isoformat()}

            if request.title is not None:
                update_data["title"] = request.title
                span.set_attribute("updated_title", True)
            if request.description is not None:
                update_data["description"] = request.description
                span.set_attribute("updated_description", True)
            if request.status is not None:
                update_data["status"] = request.status
                span.set_attribute("new_status", request.status)
                logfire_logger.info(f"[Backend] Received status update: {request.status}")
            if request.assignee is not None:
                update_data["assignee"] = request.assignee
                span.set_attribute("new_assignee", request.assignee)
            if request.task_order is not None:
                update_data["task_order"] = request.task_order
                span.set_attribute("new_task_order", request.task_order)
            if request.feature is not None:
                update_data["feature"] = request.feature
                span.set_attribute("updated_feature", True)

            # Update task in database
            logfire_logger.info(f"[Backend] Attempting Supabase update for task {task_id} with data: {update_data}")
            response = supabase_client.table("tasks").update(update_data).eq("id", task_id).execute()
            
            if response.data:
                updated_task = response.data[0]
                logfire_logger.info("Task updated successfully", 
                                  task_id=task_id, 
                                  project_id=project_id,
                                  updated_fields=list(update_data.keys()))
                logfire_logger.info(f"[Backend] Supabase response data: {updated_task}")
                span.set_attribute("success", True)
                
                # Broadcast real-time update to connected clients
                await task_update_manager.broadcast_task_update(
                    project_id=project_id,
                    event_type="task_updated",
                    task_data=updated_task
                )
                
                return {"message": "Task updated successfully", "task": updated_task}
            else:
                logfire_logger.error(f"[Backend] Supabase update returned no data for task {task_id}. Response: {response}")
                raise HTTPException(status_code=500, detail="Failed to update task")
                
        except HTTPException:
            raise
        except Exception as e:
            logfire_logger.error("Failed to update task", error=str(e), task_id=task_id)
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Archive a task (soft delete) with real-time WebSocket broadcasting."""
    with logfire_logger.span("api_archive_task") as span:
        span.set_attribute("endpoint", f"/tasks/{task_id}")
        span.set_attribute("method", "DELETE")
        span.set_attribute("task_id", task_id)
        
        try:
            supabase_client = get_supabase_client()
            
            # First get the task to get project_id for broadcasting
            # Handle backwards compatibility - check for archived field and treat NULL as False
            task_response = supabase_client.table("tasks").select("*").eq("id", task_id).execute()
            if not task_response.data:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
            task_to_archive = task_response.data[0]
            # Check if task is already archived (handle NULL as False for backwards compatibility)
            if task_to_archive.get("archived") is True:
                raise HTTPException(status_code=404, detail=f"Task {task_id} is already archived")
            project_id = task_to_archive["project_id"]
            span.set_attribute("project_id", project_id)
            
            # Archive task using soft delete (set archived=true)
            archive_data = {
                "archived": True,
                "archived_at": datetime.now().isoformat(),
                "archived_by": "api",  # Could be enhanced to track actual user
                "updated_at": datetime.now().isoformat()
            }
            
            response = supabase_client.table("tasks").update(archive_data).eq("id", task_id).execute()
            
            if response.data:
                archived_task = response.data[0]
                
                # Also archive all subtasks - use OR condition to handle NULL values
                subtasks_response = supabase_client.table("tasks").update(archive_data).eq("parent_task_id", task_id).or_("archived.is.null,archived.eq.false").execute()
                subtasks_count = len(subtasks_response.data) if subtasks_response.data else 0
                
                logfire_logger.info("Task archived successfully", 
                                  task_id=task_id, 
                                  project_id=project_id,
                                  subtasks_archived=subtasks_count)
                span.set_attribute("success", True)
                span.set_attribute("subtasks_archived", subtasks_count)
                
                # Broadcast real-time update to connected clients
                await task_update_manager.broadcast_task_update(
                    project_id=project_id,
                    event_type="task_archived",
                    task_data=archived_task
                )
                
                return {
                    "message": "Task archived successfully", 
                    "task": archived_task,
                    "subtasks_archived": subtasks_count
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to archive task")
                
        except HTTPException:
            raise
        except Exception as e:
            logfire_logger.error("Failed to archive task", error=str(e), task_id=task_id)
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/project-creation-progress/{progress_id}")
async def websocket_project_creation_progress(websocket: WebSocket, progress_id: str):
    """WebSocket endpoint for tracking specific project creation progress."""
    await project_creation_manager.add_websocket(progress_id, websocket)
    
    try:
        while True:
            # Keep connection alive with ping
            await asyncio.sleep(1)
            await websocket.send_json({"type": "ping"})
            
    except WebSocketDisconnect:
        project_creation_manager.remove_websocket(progress_id, websocket)
    except Exception as e:
        print(f"Project creation WebSocket error for progress {progress_id}: {e}")
        project_creation_manager.remove_websocket(progress_id, websocket)
        try:
            await websocket.close()
        except:
            pass

# Enhanced WebSocket endpoint with session-based change detection
@router.websocket("/projects/{project_id}/tasks/ws")
async def task_updates_websocket(websocket: WebSocket, project_id: str, session_id: str = Query(None)):
    """WebSocket endpoint for real-time task updates with session-based MCP change detection"""
    try:
        await websocket.accept()
        
        # Use session_id if provided, otherwise generate one for this connection
        if not session_id:
            session_id = str(uuid.uuid4())
            
        logfire_logger.info("Task WebSocket connected", project_id=project_id, session_id=session_id)
        
        # Add to both managers with session context
        await task_update_manager.connect_to_session(websocket, project_id, session_id)
        await db_change_detector.add_websocket_connection(project_id, websocket, session_id)
        
        # Send initial task state
        supabase_client = get_supabase_client()
        # Match the main API query exactly - handle NULL archived values
        query = supabase_client.table("tasks").select("*").eq("project_id", project_id)
        query = query.or_("archived.is.null,archived.eq.false")
        tasks_response = query.order("task_order").execute()
        
        initial_data = {
            "type": "initial_tasks",
            "data": {
                "project_id": project_id,
                "session_id": session_id,
                "tasks": tasks_response.data if tasks_response.data else []
            }
        }
        await websocket.send_json(initial_data)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "data": {
                "project_id": project_id,
                "session_id": session_id,
                "message": "Connected to task updates with session-based MCP change detection"
            },
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if message == "ping":
                    await websocket.send_json({"type": "pong", "session_id": session_id})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat", "session_id": session_id})
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        logfire_logger.info("Task updates WebSocket disconnected", project_id=project_id, session_id=session_id)
    except Exception as e:
        logfire_logger.error("Unexpected error in task updates WebSocket", project_id=project_id, session_id=session_id, error=str(e))
    finally:
        task_update_manager.disconnect_from_session(websocket, project_id, session_id)
        db_change_detector.remove_websocket_connection(project_id, websocket, session_id)

@router.websocket("/projects/stream")
async def websocket_projects_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time project list updates."""
    await project_list_manager.connect(websocket)
    try:
        # Send initial project list immediately
        await project_list_manager.send_project_list(websocket)
        
        # Keep connection alive and listen for updates
        while True:
            await asyncio.sleep(5)  # Check for updates every 5 seconds
            # Send heartbeat
            await websocket.send_json({"type": "heartbeat"})
            
    except WebSocketDisconnect:
        project_list_manager.disconnect(websocket)
    except Exception as e:
        logfire_logger.error("Projects stream WebSocket error", error=str(e))
        project_list_manager.disconnect(websocket)

# MCP CONTEXT MANAGER FOR TASK UPDATES WITH WEBSOCKET BROADCASTING
# Following the same pattern as RAG module

class TaskContext:
    """Minimal context for task MCP calls with WebSocket broadcasting support."""
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.progress_callback = None

@router.get("/tasks/subtasks/{parent_task_id}")
async def get_task_subtasks(parent_task_id: str, include_closed: bool = False):
    """Get all subtasks of a specific task."""
    with logfire_logger.span("api_get_task_subtasks") as span:
        span.set_attribute("endpoint", f"/tasks/subtasks/{parent_task_id}")
        span.set_attribute("method", "GET")
        span.set_attribute("parent_task_id", parent_task_id)
        span.set_attribute("include_closed", include_closed)
        
        try:
            supabase_client = get_supabase_client()
            
            # Set up query
            query = supabase_client.table("tasks").select("*").eq("parent_task_id", parent_task_id)
            
            # Filter out archived tasks
            query = query.eq("archived", False)
            
            # Filter out done tasks if include_closed is False
            if not include_closed:
                query = query.neq("status", "done")
            
            # Execute query
            response = query.execute()
            
            if response.data:
                logfire_logger.info("Retrieved subtasks successfully", 
                                  parent_task_id=parent_task_id,
                                  subtask_count=len(response.data),
                                  include_closed=include_closed)
                span.set_attribute("success", True)
                span.set_attribute("subtask_count", len(response.data))
                return {"tasks": response.data}
            else:
                logfire_logger.info("No subtasks found", parent_task_id=parent_task_id)
                span.set_attribute("success", True)
                span.set_attribute("subtask_count", 0)
                return {"tasks": []}
                
        except Exception as e:
            logfire_logger.error("Failed to get subtasks", error=str(e), parent_task_id=parent_task_id)
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@router.put("/mcp/tasks/{task_id}/status")
async def mcp_update_task_status_with_websockets(task_id: str, status: str):
    """Update task status via MCP tools with WebSocket broadcasting using RAG pattern."""
    with logfire_logger.span("mcp_task_status_update") as span:
        span.set_attribute("endpoint", f"/api/mcp/tasks/{task_id}/status")
        span.set_attribute("method", "PUT")
        span.set_attribute("task_id", task_id)
        span.set_attribute("status", status)
        
        try:
            logfire_logger.info("MCP task status update", task_id=task_id, status=status)
            
            # Get task to determine project_id
            supabase_client = get_supabase_client()
            task_response = supabase_client.table("tasks").select("*").eq("id", task_id).execute()
            if not task_response.data:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
            current_task = task_response.data[0]
            project_id = current_task["project_id"]
            span.set_attribute("project_id", project_id)
            
            # Create context for MCP function (like RAG does)
            ctx = TaskContext(project_id)
            
            # Set progress callback for WebSocket broadcasting
            async def websocket_callback(event_type: str, task_data: dict):
                """Callback to broadcast WebSocket updates"""
                await task_update_manager.broadcast_task_update(
                    project_id=project_id,
                    event_type=event_type,
                    task_data=task_data
                )
            
            ctx.progress_callback = websocket_callback
            
            # Import and call MCP function directly with context
            from ..modules.project_module import update_task_status_direct
            result = await update_task_status_direct(ctx, task_id, status)
            
            # Parse result
            if isinstance(result, str):
                result_data = json.loads(result)
            else:
                result_data = result
            
            if not result_data.get("success"):
                raise HTTPException(status_code=500, detail=result_data.get("error", "Unknown error"))
            
            span.set_attribute("success", True)
            logfire_logger.info("Task status updated with WebSocket broadcast", 
                              task_id=task_id, 
                              project_id=project_id, 
                              status=status)
            
            return {"message": "Task status updated successfully", "task": result_data.get("task")}
            
        except HTTPException:
            raise
        except Exception as e:
            logfire_logger.error("Failed to update task status with WebSocket", error=str(e), task_id=task_id)
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))
