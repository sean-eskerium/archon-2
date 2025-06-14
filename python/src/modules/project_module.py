"""
Project Module for Archon MCP Server

This module provides tools for:
- Project management (create, list, get, delete projects)
- Task management (create, list, update, delete tasks)
- Task status workflow (todo → doing → blocked → done)
- Task hierarchy (subtasks with parent relationships)

All tools work with the Supabase tasks and projects tables.

Enhanced with comprehensive error handling and robustness features.
"""
from mcp.server.fastmcp import FastMCP, Context
from typing import List, Dict, Any, Optional
import json
import uuid
import logging
import traceback
from datetime import datetime

# Import Logfire
from ..logfire_config import mcp_logger, api_logger

# Note: WebSocket broadcasting happens at FastAPI endpoint level

# Setup logging for the project module
logger = logging.getLogger(__name__)

def create_fallback_prd(title: str) -> Dict[str, Any]:
    """Create a basic PRD structure when Pydantic models are not available."""
    return {
        "title": f"{title} - Requirements",
        "description": f"Product Requirements Document for {title}",
        "version": "1.0",
        "goals": [],
        "user_stories": [],
        "scope": "",
        "success_criteria": []
    }

def create_project_success_response(project: Dict[str, Any], warning: str = None) -> str:
    """Create a standardized project success response."""
    response = {
        "success": True,
        "project": {
            "id": project["id"],
            "title": project["title"],
            "github_repo": project.get("github_repo"),
            "created_at": project["created_at"]
        }
    }
    if warning:
        response["warning"] = warning
    return json.dumps(response)

def validate_task_status(status: str) -> tuple[bool, str]:
    """Validate task status and return (is_valid, error_message)."""
    valid_statuses = ['todo', 'doing', 'review', 'done']
    if status not in valid_statuses:
        return False, f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
    return True, ""

def safe_get_supabase_client(ctx: Context) -> tuple[Any, str]:
    """Safely get Supabase client with error handling. Returns (client, error_message)."""
    try:
        client = ctx.request_context.lifespan_context.supabase_client
        return client, ""
    except AttributeError as e:
        logger.error(f"Failed to get Supabase client: {e}")
        return None, "Database connection not available"

# Import our new models with error handling
try:
    from .models import (
        ProjectRequirementsDocument, 
        GeneralDocument, 
        DocumentType,
        CreateDocumentRequest,
        UpdateDocumentRequest,
        create_default_prd,
        create_default_document
    )
    MODELS_AVAILABLE = True
    logger.info("✓ Project models imported successfully")
except ImportError as e:
    # Fallback if models module not available yet
    logger.warning(f"⚠ Models module not available: {e} - using basic functionality")
    MODELS_AVAILABLE = False


def register_project_tools(mcp: FastMCP):
    """Register all project and task management tools with the MCP server."""
    
    @mcp.tool()
    async def create_project(ctx: Context, title: str, prd: Dict[str, Any] = None, github_repo: str = None) -> str:
        """
        Create a new project with a default PRD document.
        
        Args:
            title: Title of the project
            prd: Optional product requirements document as JSON
            github_repo: Optional GitHub repository URL
        
        Returns:
            JSON string with the created project information
        """
        with mcp_logger.span("mcp_create_project") as span:
            span.set_attribute("tool", "create_project")
            span.set_attribute("title", title)
            span.set_attribute("has_github_repo", github_repo is not None)
            span.set_attribute("has_prd", prd is not None)
            
            try:
                logger.info(f"Creating project: {title}")
                mcp_logger.info("Creating new project", title=title, github_repo=github_repo)
                
                # Validate inputs
                if not title or not isinstance(title, str) or len(title.strip()) == 0:
                    error_msg = "Project title is required and must be a non-empty string"
                    mcp_logger.error("Project creation failed - invalid title", title=title)
                    span.set_attribute("success", False)
                    span.set_attribute("error", error_msg)
                    return json.dumps({
                        "success": False,
                        "error": error_msg
                    })
                
                # Get Supabase client with error handling
                try:
                    # Get the Supabase client from the context
                    supabase_client = ctx.request_context.lifespan_context.supabase_client
                except AttributeError as e:
                    logger.error(f"Failed to get Supabase client: {e}")
                    error_msg = "Database connection not available"
                    mcp_logger.error("Project creation failed - no database connection", error=str(e))
                    span.set_attribute("success", False)
                    span.set_attribute("error", error_msg)
                    return json.dumps({
                        "success": False,
                        "error": error_msg
                    })
                
                # Create the project first
                project_data = {
                    "title": title.strip(),
                    "docs": [],  # Will add PRD as a document in docs array after project creation
                    "features": [],
                    "data": [],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                if github_repo and isinstance(github_repo, str) and len(github_repo.strip()) > 0:
                    project_data["github_repo"] = github_repo.strip()
                
                try:
                    response = supabase_client.table("projects").insert(project_data).execute()
                    
                    if not response.data:
                        logger.error("Supabase returned empty data for project creation")
                        error_msg = "Failed to create project - database returned no data"
                        mcp_logger.error("Project creation failed - empty database response")
                        span.set_attribute("success", False)
                        span.set_attribute("error", error_msg)
                        return json.dumps({
                            "success": False,
                            "error": error_msg
                        })
                    
                    project = response.data[0]
                    project_id = project["id"]
                    logger.info(f"Project created successfully with ID: {project_id}")
                    mcp_logger.info("Project created successfully", project_id=project_id, title=title)
                    span.set_attribute("project_id", project_id)
                    
                    # Create PRD document in the docs array
                    try:
                        # Format the PRD content
                        prd_content = prd or create_fallback_prd(title)
                        
                        # Create PRD document
                        prd_doc_title = f"{title} - Product Requirements Document"
                        doc_response = await add_project_document(
                            ctx=ctx,
                            project_id=project_id,
                            document_type="prd",
                            title=prd_doc_title,
                            content=prd_content,
                            tags=["prd", "requirements"],
                            author="System"
                        )
                        
                        # Parse the response to check for success
                        doc_result = json.loads(doc_response)
                        if not doc_result.get("success"):
                            logger.warning(f"Failed to create PRD document: {doc_result.get('error')}")
                            mcp_logger.warning("Failed to create PRD document", error=doc_result.get('error'))
                            # Continue with project creation but return a warning
                            return create_project_success_response(project, warning="Project created but PRD document creation failed")
                            
                    except Exception as doc_error:
                        logger.warning(f"Error creating PRD document: {doc_error}")
                        mcp_logger.warning("Error creating PRD document", error=str(doc_error))
                        return create_project_success_response(project, warning="Project created but PRD document creation failed")
                        
                    # All successful - return success response with project info
                    return create_project_success_response(project)
                    
                except Exception as db_error:
                    logger.error(f"Database error creating project: {db_error}")
                    logger.error(traceback.format_exc())
                    error_msg = f"Database error: {str(db_error)}"
                    mcp_logger.error("Project creation failed - database error", error=str(db_error), error_type=type(db_error).__name__)
                    span.set_attribute("success", False)
                    span.set_attribute("error", error_msg)
                    return json.dumps({
                        "success": False,
                        "error": error_msg
                    })
            
            except Exception as e:
                logger.error(f"Unexpected error creating project: {e}")
                logger.error(traceback.format_exc())
                error_msg = f"Unexpected error creating project: {str(e)}"
                mcp_logger.error("Project creation failed - unexpected error", error=str(e))
                span.set_attribute("success", False)
                span.set_attribute("error", error_msg)
                return json.dumps({
                    "success": False,
                    "error": error_msg
                })
    
    @mcp.tool()
    async def list_projects(ctx: Context) -> str:
        """
        List all projects.
        
        Returns:
            JSON string with list of all projects
        """
        try:
            # Get the Supabase client from the context
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            response = supabase_client.table("projects").select("*").order("created_at", desc=True).execute()
            
            projects = []
            for project in response.data:
                projects.append({
                    "id": project["id"],
                    "title": project["title"],
                    "github_repo": project.get("github_repo"),
                    "created_at": project["created_at"],
                    "updated_at": project["updated_at"]
                })
            
            return json.dumps({
                "success": True,
                "projects": projects,
                "total_count": len(projects)
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error listing projects: {str(e)}"
            })
    
    @mcp.tool()
    async def get_project(ctx: Context, project_id: str) -> str:
        """
        Get a specific project by ID.
        
        Args:
            project_id: UUID of the project
        
        Returns:
            JSON string with project details
        """
        try:
            # Get the Supabase client from the context
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
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
                
                # Add sources to project data
                project["technical_sources"] = technical_sources
                project["business_sources"] = business_sources
                
                return json.dumps({
                    "success": True,
                    "project": project
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Project with ID {project_id} not found"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error getting project: {str(e)}"
            })
    
    @mcp.tool()
    async def delete_project(ctx: Context, project_id: str) -> str:
        """
        Delete a project and all its associated tasks.
        
        Args:
            project_id: UUID of the project to delete
        
        Returns:
            JSON string with deletion results
        """
        try:
            # Get the Supabase client from the context
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            # First, get task count for reporting
            tasks_response = supabase_client.table("tasks").select("id").eq("project_id", project_id).execute()
            tasks_count = len(tasks_response.data) if tasks_response.data else 0
            
            # Delete the project (tasks will be deleted by cascade)
            response = supabase_client.table("projects").delete().eq("id", project_id).execute()
            
            if response.data:
                return json.dumps({
                    "success": True,
                    "project_id": project_id,
                    "deleted_tasks": tasks_count
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Project with ID {project_id} not found"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error deleting project: {str(e)}"
            })
    
    @mcp.tool()
    async def create_task(ctx: Context, project_id: str, title: str, description: str = "", assignee: str = "User", task_order: int = 0, feature: str = None, parent_task_id: str = None, sources: List[Dict[str, Any]] = None, code_examples: List[Dict[str, Any]] = None) -> str:
        """
        Create a new task under a project.
        
        Args:
            project_id: UUID of the parent project
            title: Title of the task
            description: Optional detailed description
            assignee: Task assignee - one of 'User', 'Archon', 'AI IDE Agent' (default: 'User')
            task_order: Order/priority of the task (default: 0)
            feature: Optional feature name/label this task belongs to
            parent_task_id: Optional UUID of parent task for subtasks
            sources: Optional list of source metadata dicts
            code_examples: Optional list of code example dicts
        
        Returns:
            JSON string with the created task information
        """
        with mcp_logger.span("mcp_create_task") as span:
            span.set_attribute("tool", "create_task")
            span.set_attribute("project_id", project_id)
            span.set_attribute("title", title)
            span.set_attribute("assignee", assignee)
            span.set_attribute("task_order", task_order)
            span.set_attribute("has_parent", parent_task_id is not None)
            span.set_attribute("has_sources", sources is not None and len(sources) > 0 if sources else False)
            
            try:
                logger.info(f"Creating task: {title} for project {project_id}")
                mcp_logger.info("Creating new task", title=title, project_id=project_id, assignee=assignee)
                
                # Validate inputs
                if not title or not isinstance(title, str) or len(title.strip()) == 0:
                    error_msg = "Task title is required and must be a non-empty string"
                    mcp_logger.error("Task creation failed - invalid title", title=title, project_id=project_id)
                    span.set_attribute("success", False)
                    span.set_attribute("error", error_msg)
                    return json.dumps({
                        "success": False,
                        "error": error_msg
                    })
                
                if not project_id or not isinstance(project_id, str):
                    error_msg = "Project ID is required and must be a string"
                    mcp_logger.error("Task creation failed - invalid project_id", project_id=project_id)
                    span.set_attribute("success", False)
                    span.set_attribute("error", error_msg)
                    return json.dumps({
                        "success": False,
                        "error": error_msg
                    })
                
                # Validate assignee
                valid_assignees = ['User', 'Archon', 'AI IDE Agent']
                if assignee not in valid_assignees:
                    error_msg = f"Invalid assignee '{assignee}'. Must be one of: {', '.join(valid_assignees)}"
                    mcp_logger.error("Task creation failed - invalid assignee", assignee=assignee, valid_assignees=valid_assignees)
                    span.set_attribute("success", False)
                    span.set_attribute("error", error_msg)
                    return json.dumps({
                        "success": False,
                        "error": error_msg
                    })
                
                # Get Supabase client
                supabase_client, error = safe_get_supabase_client(ctx)
                if error:
                    mcp_logger.error("Task creation failed - no database connection", error=error)
                    span.set_attribute("success", False)
                    span.set_attribute("error", error)
                    return json.dumps({
                        "success": False,
                        "error": error
                    })
                
                task_data = {
                    "project_id": project_id,
                    "title": title,
                    "description": description,
                    "status": "todo",
                    "assignee": assignee,
                    "task_order": task_order,
                    "sources": sources or [],
                    "code_examples": code_examples or [],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                if parent_task_id:
                    task_data["parent_task_id"] = parent_task_id
                
                if feature:
                    task_data["feature"] = feature
                
                response = supabase_client.table("tasks").insert(task_data).execute()
                
                if response.data:
                    task = response.data[0]
                    return json.dumps({
                        "success": True,
                        "task": {
                            "id": task["id"],
                            "project_id": task["project_id"],
                            "parent_task_id": task.get("parent_task_id"),
                            "title": task["title"],
                            "description": task["description"],
                            "status": task["status"],
                            "assignee": task["assignee"],
                            "task_order": task["task_order"],
                            "created_at": task["created_at"]
                        }
                    })
                else:
                    return json.dumps({
                        "success": False,
                        "error": "Failed to create task"
                    })
                
            except Exception as e:
                logger.error(f"Unexpected error creating task: {e}")
                logger.error(traceback.format_exc())
                error_msg = f"Unexpected error creating task: {str(e)}"
                mcp_logger.error("Task creation failed - unexpected error", error=str(e))
                span.set_attribute("success", False)
                span.set_attribute("error", error_msg)
                return json.dumps({
                    "success": False,
                    "error": error_msg
                })
    
    @mcp.tool()
    async def list_tasks_by_project(ctx: Context, project_id: str, include_closed: bool = False) -> str:
        """
        List all tasks under a specific project.
        
        Args:
            project_id: UUID of the project
            include_closed: Whether to include closed/done tasks (default: False)
        
        Returns:
            JSON string with list of tasks for the project
        """
        try:
            # Get the Supabase client from the context
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            # Build query - always filter out archived tasks (handle NULL as False), and optionally filter out 'done' tasks
            query = supabase_client.table("tasks").select("*").eq("project_id", project_id).or_("archived.is.null,archived.eq.false")
            
            if not include_closed:
                # Filter out closed/done tasks to focus on active work
                query = query.neq("status", "done")
            
            response = query.order("task_order", desc=False).order("created_at", desc=False).execute()
            
            tasks = []
            for task in response.data:
                tasks.append({
                    "id": task["id"],
                    "project_id": task["project_id"],
                    "parent_task_id": task.get("parent_task_id"),
                    "title": task["title"],
                    "description": task["description"],
                    "status": task["status"],
                    "assignee": task.get("assignee", "User"),
                    "task_order": task.get("task_order", 0),
                    "created_at": task["created_at"],
                    "updated_at": task["updated_at"]
                })
            
            filter_note = " (excluding closed tasks)" if not include_closed else " (including all tasks)"
            filter_note += " (archived tasks always excluded)"
            
            return json.dumps({
                "success": True,
                "project_id": project_id,
                "tasks": tasks,
                "total_count": len(tasks),
                "filter_applied": filter_note,
                "include_closed": include_closed
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error listing tasks: {str(e)}"
            })
    
    @mcp.tool()
    async def get_task(ctx: Context, task_id: str) -> str:
        """
        Get a specific task by ID.
        
        Args:
            ctx: The MCP server provided context
            task_id: UUID of the task
        
        Returns:
            JSON string with task details
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            response = supabase_client.table("tasks").select("*").eq("id", task_id).execute()
            
            if response.data:
                task = response.data[0]
                return json.dumps({
                    "success": True,
                    "task": task
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Task with ID {task_id} not found"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error getting task: {str(e)}"
            })
    
    @mcp.tool()
    async def update_task_status(ctx: Context, task_id: str, status: str) -> str:
        """
        Update a task's status.
        
        Args:
            ctx: The MCP server provided context
            task_id: UUID of the task to update
            status: New status - one of 'todo', 'doing', 'review', 'done'
        
        Returns:
            JSON string with update results
        """
        with mcp_logger.span("mcp_update_task_status") as span:
            span.set_attribute("tool", "update_task_status")
            span.set_attribute("task_id", task_id)
            span.set_attribute("new_status", status)
            
            try:
                logger.info(f"Updating task {task_id} status to {status}")
                mcp_logger.info("Updating task status", task_id=task_id, new_status=status)
                
                # Validate status
                is_valid, error_msg = validate_task_status(status)
                if not is_valid:
                    mcp_logger.error("Task status update failed - invalid status", task_id=task_id, status=status, error=error_msg)
                    span.set_attribute("success", False)
                    span.set_attribute("error", error_msg)
                    return json.dumps({
                        "success": False,
                        "error": error_msg
                    })
                
                # Get Supabase client
                supabase_client, db_error = safe_get_supabase_client(ctx)
                if db_error:
                    mcp_logger.error("Task status update failed - no database connection", task_id=task_id, error=db_error)
                    span.set_attribute("success", False)
                    span.set_attribute("error", db_error)
                    return json.dumps({
                        "success": False,
                        "error": db_error
                    })
                
                try:
                    # Update the task status directly in database
                    response = supabase_client.table("tasks").update({
                        "status": status,
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", task_id).execute()
                    
                    if response.data:
                        task = response.data[0]
                        logger.info(f"Task {task_id} status updated successfully to {status}")
                        mcp_logger.info("Task status updated successfully", 
                                      task_id=task_id, 
                                      old_status=task.get("status"), 
                                      new_status=status)
                        span.set_attribute("success", True)
                        span.set_attribute("old_status", task.get("status"))
                        
                        # Check for progress callback and broadcast WebSocket update
                        progress_callback = getattr(ctx, 'progress_callback', None)
                        if progress_callback:
                            try:
                                await progress_callback(
                                    event_type="task_updated",
                                    task_data=task
                                )
                                logger.info(f"WebSocket update broadcast for task {task_id}")
                            except Exception as ws_error:
                                logger.warning(f"Failed to broadcast WebSocket update: {ws_error}")
                        
                        return json.dumps({
                            "success": True,
                            "task": task
                        })
                    else:
                        error_msg = f"Task with ID {task_id} not found"
                        mcp_logger.error("Task status update failed - task not found", task_id=task_id)
                        span.set_attribute("success", False)
                        span.set_attribute("error", error_msg)
                        return json.dumps({
                            "success": False,
                            "error": error_msg
                        })
                        
                except Exception as db_error:
                    logger.error(f"Database error updating task status: {db_error}")
                    error_msg = f"Database error: {str(db_error)}"
                    mcp_logger.error("Task status update failed - database error", 
                                   task_id=task_id, 
                                   error=str(db_error), 
                                   error_type=type(db_error).__name__)
                    span.set_attribute("success", False)
                    span.set_attribute("error", error_msg)
                    return json.dumps({
                        "success": False,
                        "error": error_msg
                    })
                    
            except Exception as e:
                logger.error(f"Unexpected error updating task status: {e}")
                logger.error(traceback.format_exc())
                error_msg = f"Unexpected error: {str(e)}"
                mcp_logger.error("Task status update failed - unexpected error", 
                               task_id=task_id, 
                               error=str(e))
                span.set_attribute("success", False)
                span.set_attribute("error", error_msg)
                return json.dumps({
                    "success": False,
                    "error": error_msg
                })
    
    @mcp.tool()
    async def update_task(ctx: Context, task_id: str, title: str = None, description: str = None, status: str = None, assignee: str = None, task_order: int = None, feature: str = None) -> str:
        """
        Update task details.
        
        Args:
            ctx: The MCP server provided context
            task_id: UUID of the task to update
            title: Optional new title
            description: Optional new description  
            status: Optional new status - one of 'todo', 'doing', 'review', 'done'
            assignee: Optional new assignee - one of 'User', 'Archon', 'AI IDE Agent'
            task_order: Optional new order/priority
            feature: Optional new feature name/label
        
        Returns:
            JSON string with update results
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            # Build update data
            update_data = {
                "updated_at": datetime.now().isoformat()
            }
            
            if title is not None:
                update_data["title"] = title
            
            if description is not None:
                update_data["description"] = description
                
            if status is not None:
                valid_statuses = ['todo', 'doing', 'review', 'done']
                if status not in valid_statuses:
                    return json.dumps({
                        "success": False,
                        "error": f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
                    })
                update_data["status"] = status
            
            if assignee is not None:
                valid_assignees = ['User', 'Archon', 'AI IDE Agent']
                if assignee not in valid_assignees:
                    return json.dumps({
                        "success": False,
                        "error": f"Invalid assignee '{assignee}'. Must be one of: {', '.join(valid_assignees)}"
                    })
                update_data["assignee"] = assignee
            
            if task_order is not None:
                update_data["task_order"] = task_order
            
            if feature is not None:
                update_data["feature"] = feature
            
            # Directly update database (WebSocket broadcasting happens at FastAPI endpoint level)
            response = supabase_client.table("tasks").update(update_data).eq("id", task_id).execute()
            
            if response.data:
                task = response.data[0]
                
                # Check for progress callback and broadcast WebSocket update
                progress_callback = getattr(ctx, 'progress_callback', None)
                if progress_callback:
                    try:
                        await progress_callback(
                            event_type="task_updated",
                            task_data=task
                        )
                        logger.info(f"WebSocket update broadcast for task {task_id}")
                    except Exception as ws_error:
                        logger.warning(f"Failed to broadcast WebSocket update: {ws_error}")
                
                return json.dumps({
                    "success": True,
                    "task": task,
                    "message": "Task updated successfully"
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Task with ID {task_id} not found"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error updating task: {str(e)}"
            })
    
    @mcp.tool()
    async def delete_task(ctx: Context, task_id: str) -> str:
        """
        Archive a task and all its subtasks (soft delete).
        
        Args:
            ctx: The MCP server provided context
            task_id: UUID of the task to archive
        
        Returns:
            JSON string with archive results
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            # First, check if task exists and is not already archived
            task_response = supabase_client.table("tasks").select("*").eq("id", task_id).execute()
            if not task_response.data:
                return json.dumps({
                    "success": False,
                    "error": f"Task with ID {task_id} not found"
                })
            
            task = task_response.data[0]
            # Check if task is already archived (handle NULL as False for backwards compatibility)
            if task.get("archived") is True:
                return json.dumps({
                    "success": False,
                    "error": f"Task with ID {task_id} is already archived"
                })
            
            # Get all non-archived subtasks to count them (handle NULL as False)
            subtasks_response = supabase_client.table("tasks").select("id").eq("parent_task_id", task_id).or_("archived.is.null,archived.eq.false").execute()
            subtasks_count = len(subtasks_response.data) if subtasks_response.data else 0
            
            # Archive the task using soft delete
            from datetime import datetime
            archive_data = {
                "archived": True,
                "archived_at": datetime.now().isoformat(),
                "archived_by": "mcp",
                "updated_at": datetime.now().isoformat()
            }
            
            # Archive the main task
            response = supabase_client.table("tasks").update(archive_data).eq("id", task_id).execute()
            
            if response.data:
                # Also archive all subtasks
                if subtasks_count > 0:
                    subtasks_response = supabase_client.table("tasks").update(archive_data).eq("parent_task_id", task_id).or_("archived.is.null,archived.eq.false").execute()
                
                return json.dumps({
                    "success": True,
                    "task_id": task_id,
                    "archived_subtasks": subtasks_count,
                    "message": "Task and all subtasks archived successfully"
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to archive task {task_id}"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error archiving task: {str(e)}"
            })
    
    @mcp.tool()
    async def get_task_subtasks(ctx: Context, parent_task_id: str, include_closed: bool = False) -> str:
        """
        Get all subtasks of a specific task.
        
        Args:
            ctx: The MCP server provided context
            parent_task_id: UUID of the parent task
            include_closed: Whether to include closed/done subtasks (default: False)
        
        Returns:
            JSON string with list of subtasks
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            # Build query - always filter out archived subtasks (handle NULL as False), and optionally filter out 'done' subtasks
            query = supabase_client.table("tasks").select("*").eq("parent_task_id", parent_task_id).or_("archived.is.null,archived.eq.false")
            
            if not include_closed:
                # Filter out closed/done subtasks to focus on active work
                query = query.neq("status", "done")
            
            response = query.order("task_order", desc=False).order("created_at", desc=False).execute()
            
            subtasks = []
            for task in response.data:
                subtasks.append({
                    "id": task["id"],
                    "project_id": task["project_id"],
                    "parent_task_id": task["parent_task_id"],
                    "title": task["title"],
                    "description": task["description"],
                    "status": task["status"],
                    "assignee": task.get("assignee", "User"),
                    "task_order": task.get("task_order", 0),
                    "created_at": task["created_at"],
                    "updated_at": task["updated_at"]
                })
            
            filter_note = " (excluding closed subtasks)" if not include_closed else " (including all subtasks)"
            
            return json.dumps({
                "success": True,
                "parent_task_id": parent_task_id,
                "subtasks": subtasks,
                "total_count": len(subtasks),
                "filter_applied": filter_note,
                "include_closed": include_closed
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error getting subtasks: {str(e)}"
            })
    
    @mcp.tool()
    async def get_tasks_by_status(ctx: Context, project_id: str, status: str) -> str:
        """
        Get all tasks in a project filtered by status.
        
        Args:
            ctx: The MCP server provided context
            project_id: UUID of the project
            status: Status to filter by - one of 'todo', 'doing', 'review', 'done'
        
        Returns:
            JSON string with filtered tasks
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            # Validate status
            valid_statuses = ['todo', 'doing', 'review', 'done']
            if status not in valid_statuses:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
                })
            
            response = supabase_client.table("tasks").select("*").eq("project_id", project_id).eq("status", status).or_("archived.is.null,archived.eq.false").order("task_order", desc=False).order("created_at", desc=False).execute()
            
            tasks = []
            for task in response.data:
                tasks.append({
                    "id": task["id"],
                    "project_id": task["project_id"],
                    "parent_task_id": task.get("parent_task_id"),
                    "title": task["title"],
                    "description": task["description"],
                    "status": task["status"],
                    "assignee": task.get("assignee", "User"),
                    "task_order": task.get("task_order", 0),
                    "created_at": task["created_at"],
                    "updated_at": task["updated_at"]
                })
            
            return json.dumps({
                "success": True,
                "project_id": project_id,
                "status_filter": status,
                "tasks": tasks,
                "total_count": len(tasks)
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error getting tasks by status: {str(e)}"
            })

    @mcp.tool()
    async def get_project_features(ctx: Context, project_id: str) -> str:
        """
        Get features from a project's features JSONB field.
        
        Args:
            project_id: UUID of the project
        
        Returns:
            JSON string with list of features
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            response = supabase_client.table("projects").select("features").eq("id", project_id).single().execute()
            
            if not response.data:
                return json.dumps({"success": False, "error": "Project not found"})
            
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
            
            return json.dumps({
                "success": True, 
                "features": feature_options,
                "count": len(feature_options)
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error getting project features: {str(e)}"
            })

    # Document Operations for docs JSONB field
    
    @mcp.tool()
    async def add_project_document(ctx: Context, project_id: str, document_type: str, title: str, content: Dict[str, Any] = None, tags: List[str] = None, author: str = None) -> str:
        """
        Add a new document to a project's docs JSONB field using clean MCP format.
        
        CRITICAL: The content field must use the structured MCP format for optimal AI agent consumption.
        The UI will automatically convert this to editable blocks.
        
        Args:
            ctx: The MCP server provided context
            project_id: UUID of the parent project
            document_type: Type of document (prd, feature_plan, erd, technical_spec, meeting_notes, api_docs)
            title: Document title (e.g., "E-commerce Platform v1.0 - Product Requirements Document")
            content: Document content as structured JSON - MUST follow MCP format:
                {
                    "project_overview": {
                        "description": "Clear project description",
                        "target_completion": "Timeline or milestone"
                    },
                    "goals": ["Specific goal 1", "Specific goal 2"],
                    "scope": {
                        "frontend": "Technology description",
                        "backend": "Technology description"
                    },
                    "architecture": {
                        "frontend": ["Technology 1", "Technology 2"],
                        "backend": ["Technology 1", "Technology 2"]
                    },
                    "tech_packages": {
                        "frontend_dependencies": ["package ^version"],
                        "backend_dependencies": ["package ^version"]
                    },
                    "ui_ux_requirements": {
                        "color_palette": ["#hex1", "#hex2"],
                        "typography": {"headings": "Font", "body": "Font"}
                    },
                    "coding_standards": ["Standard 1", "Standard 2"]
                }
            tags: Optional list of tags for categorization
            author: Optional author name (defaults to "System")
        
        Returns:
            JSON string with the created document information
        
        Example:
            add_project_document(
                project_id="uuid-here",
                document_type="prd",
                title="User Authentication System - PRD",
                content={
                    "project_overview": {
                        "description": "Secure JWT-based authentication system",
                        "target_completion": "Q2 2024"
                    },
                    "goals": [
                        "Implement secure user authentication",
                        "Support multiple login methods",
                        "Ensure scalable session management"
                    ],
                    "architecture": {
                        "backend": ["FastAPI", "JWT tokens", "bcrypt hashing"],
                        "database": ["PostgreSQL", "user sessions table"]
                    }
                },
                tags=["authentication", "security", "backend"]
            )
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            # Get current project
            project_response = supabase_client.table("projects").select("docs").eq("id", project_id).execute()
            if not project_response.data:
                return json.dumps({
                    "success": False,
                    "error": f"Project with ID {project_id} not found"
                })
            
            current_docs = project_response.data[0].get("docs", [])
            
            # Create new document entry
            new_doc = {
                "id": str(uuid.uuid4()),
                "document_type": document_type,
                "title": title,
                "content": content or {},
                "tags": tags or [],
                "status": "draft",
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            if author:
                new_doc["author"] = author
            
            # Add to docs array
            updated_docs = current_docs + [new_doc]
            
            # Update project
            response = supabase_client.table("projects").update({
                "docs": updated_docs,
                "updated_at": datetime.now().isoformat()
            }).eq("id", project_id).execute()
            
            if response.data:
                return json.dumps({
                    "success": True,
                    "document": {
                        "id": new_doc["id"],
                        "project_id": project_id,
                        "document_type": new_doc["document_type"],
                        "title": new_doc["title"],
                        "status": new_doc["status"],
                        "version": new_doc["version"],
                        "created_at": new_doc["created_at"]
                    }
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": "Failed to add document to project"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error adding document: {str(e)}"
            })
    
    @mcp.tool()
    async def list_project_documents(ctx: Context, project_id: str) -> str:
        """
        List all documents in a project's docs JSONB field.
        
        Args:
            ctx: The MCP server provided context
            project_id: UUID of the project
        
        Returns:
            JSON string with list of documents for the project
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            response = supabase_client.table("projects").select("docs").eq("id", project_id).execute()
            
            if not response.data:
                return json.dumps({
                    "success": False,
                    "error": f"Project with ID {project_id} not found"
                })
            
            docs = response.data[0].get("docs", [])
            
            # Format documents for response (exclude full content for listing)
            documents = []
            for doc in docs:
                documents.append({
                    "id": doc.get("id"),
                    "document_type": doc.get("document_type"),
                    "title": doc.get("title"),
                    "status": doc.get("status"),
                    "version": doc.get("version"),
                    "tags": doc.get("tags", []),
                    "author": doc.get("author"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                })
            
            return json.dumps({
                "success": True,
                "project_id": project_id,
                "documents": documents,
                "total_count": len(documents)
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error listing documents: {str(e)}"
            })
    
    @mcp.tool()
    async def get_project_document(ctx: Context, project_id: str, doc_id: str) -> str:
        """
        Get a specific document from a project's docs JSONB field.
        
        Args:
            ctx: The MCP server provided context
            project_id: UUID of the project
            doc_id: UUID of the document
        
        Returns:
            JSON string with document details including full content
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            response = supabase_client.table("projects").select("docs").eq("id", project_id).execute()
            
            if not response.data:
                return json.dumps({
                    "success": False,
                    "error": f"Project with ID {project_id} not found"
                })
            
            docs = response.data[0].get("docs", [])
            
            # Find the specific document
            document = None
            for doc in docs:
                if doc.get("id") == doc_id:
                    document = doc
                    break
            
            if document:
                return json.dumps({
                    "success": True,
                    "document": document
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Document with ID {doc_id} not found in project {project_id}"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error getting document: {str(e)}"
            })
    
    @mcp.tool()
    async def update_project_document(ctx: Context, project_id: str, doc_id: str, title: str = None, content: Dict[str, Any] = None, status: str = None, tags: List[str] = None, author: str = None, version: str = None) -> str:
        """
        Update a document in a project's docs JSONB field using clean MCP format.
        
        CRITICAL: When updating content, must use the structured MCP format for optimal AI agent consumption.
        
        Args:
            ctx: The MCP server provided context
            project_id: UUID of the project
            doc_id: UUID of the document to update
            title: Optional new title
            content: Optional new content - MUST follow MCP format when provided:
                {
                    "project_overview": {"description": "...", "target_completion": "..."},
                    "goals": ["goal1", "goal2"],
                    "scope": {"frontend": "...", "backend": "..."},
                    "architecture": {"frontend": [...], "backend": [...]},
                    "tech_packages": {"frontend_dependencies": [...], "backend_dependencies": [...]},
                    "ui_ux_requirements": {"color_palette": [...], "typography": {...}},
                    "coding_standards": ["standard1", "standard2"]
                }
            status: Optional new status (draft, review, approved, archived)
            tags: Optional new tags for categorization
            author: Optional new author name
            version: Optional new version (e.g., "1.1", "2.0")
        
        Returns:
            JSON string with update results
        
        Example:
            update_project_document(
                project_id="uuid-here",
                doc_id="doc-uuid-here",
                content={
                    "project_overview": {
                        "description": "Updated authentication system with OAuth support",
                        "target_completion": "Q3 2024"
                    },
                    "goals": [
                        "Implement OAuth 2.0 integration",
                        "Add social login options",
                        "Maintain backward compatibility"
                    ]
                },
                status="review",
                version="1.2"
            )
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            # Get current project docs
            project_response = supabase_client.table("projects").select("docs").eq("id", project_id).execute()
            if not project_response.data:
                return json.dumps({
                    "success": False,
                    "error": f"Project with ID {project_id} not found"
                })
            
            current_docs = project_response.data[0].get("docs", [])
            
            # Create a version snapshot BEFORE making changes
            try:
                change_summary = f"Document '{doc_id}' updated"
                if title and content:
                    change_summary = f"Updated document '{title}' with new content"
                elif title:
                    change_summary = f"Updated document title to '{title}'"
                elif content:
                    change_summary = f"Updated document '{doc_id}' content"
                
                # Simple INSERT into document_versions table
                version_data = {
                    'project_id': project_id,
                    'field_name': 'docs',
                    'content': current_docs,
                    'change_summary': change_summary,
                    'change_type': 'update',
                    'document_id': doc_id,
                    'created_by': author or 'system',
                    'created_at': datetime.now().isoformat()
                }
                
                # Get current highest version number
                existing_versions = supabase_client.table("document_versions").select("version_number").eq("project_id", project_id).eq("field_name", "docs").order("version_number", desc=True).limit(1).execute()
                
                next_version = 1
                if existing_versions.data:
                    next_version = existing_versions.data[0]['version_number'] + 1
                
                version_data['version_number'] = next_version
                
                version_result = supabase_client.table("document_versions").insert(version_data).execute()
                
                if not version_result.data:
                    # Log warning but continue with update
                    logger.warning(f"Failed to create version snapshot for document {doc_id}")
            except Exception as version_error:
                logger.warning(f"Version creation failed for document {doc_id}: {version_error}")
            
            # Make a copy to modify
            docs = current_docs.copy()
            
            # Find and update the document
            updated = False
            for i, doc in enumerate(docs):
                if doc.get("id") == doc_id:
                    if title is not None:
                        docs[i]["title"] = title
                    if content is not None:
                        docs[i]["content"] = content
                    if status is not None:
                        docs[i]["status"] = status
                    if tags is not None:
                        docs[i]["tags"] = tags
                    if author is not None:
                        docs[i]["author"] = author
                    if version is not None:
                        docs[i]["version"] = version
                    docs[i]["updated_at"] = datetime.now().isoformat()
                    updated = True
                    break
            
            if not updated:
                return json.dumps({
                    "success": False,
                    "error": f"Document with ID {doc_id} not found in project {project_id}"
                })
            
            # Update the project
            response = supabase_client.table("projects").update({
                "docs": docs,
                "updated_at": datetime.now().isoformat()
            }).eq("id", project_id).execute()
            
            if response.data:
                # Find the updated document to return
                updated_doc = None
                for doc in docs:
                    if doc.get("id") == doc_id:
                        updated_doc = doc
                        break
                
                return json.dumps({
                    "success": True,
                    "document": updated_doc
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": "Failed to update document"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error updating document: {str(e)}"
            })
    
    @mcp.tool()
    async def delete_project_document(ctx: Context, project_id: str, doc_id: str) -> str:
        """
        Delete a document from a project's docs JSONB field.
        
        Args:
            ctx: The MCP server provided context
            project_id: UUID of the project
            doc_id: UUID of the document to delete
        
        Returns:
            JSON string with deletion results
        """
        try:
            supabase_client = ctx.request_context.lifespan_context.supabase_client
            
            # Get current project docs
            project_response = supabase_client.table("projects").select("docs").eq("id", project_id).execute()
            if not project_response.data:
                return json.dumps({
                    "success": False,
                    "error": f"Project with ID {project_id} not found"
                })
            
            docs = project_response.data[0].get("docs", [])
            
            # Remove the document
            original_length = len(docs)
            docs = [doc for doc in docs if doc.get("id") != doc_id]
            
            if len(docs) == original_length:
                return json.dumps({
                    "success": False,
                    "error": f"Document with ID {doc_id} not found in project {project_id}"
                })
            
            # Update the project
            response = supabase_client.table("projects").update({
                "docs": docs,
                "updated_at": datetime.now().isoformat()
            }).eq("id", project_id).execute()
            
            if response.data:
                return json.dumps({
                    "success": True,
                    "project_id": project_id,
                    "doc_id": doc_id
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": "Failed to delete document"
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error deleting document: {str(e)}"
            })

    # Direct functions for FastAPI endpoints (following RAG pattern)
    async def update_task_status_direct(ctx, task_id: str, status: str) -> str:
        """
        Direct function for updating task status that can be called from FastAPI with context.
        Follows the same pattern as RAG module's smart_crawl_url_direct.
        """
        try:
            # Get Supabase client directly
            supabase_client = get_supabase_client()
            
            # Validate status
            if status not in ["todo", "doing", "review", "done"]:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid status '{status}'. Must be one of: todo, doing, review, done"
                })
            
            # Update task status
            response = supabase_client.table("tasks").update({"status": status}).eq("id", task_id).execute()
            
            if response.data:
                task = response.data[0]
                logger.info(f"Task {task_id} status updated successfully to {status}")
                
                # Check for progress callback and broadcast WebSocket update
                progress_callback = getattr(ctx, 'progress_callback', None)
                if progress_callback:
                    try:
                        await progress_callback(
                            event_type="task_updated",
                            task_data=task
                        )
                        logger.info(f"WebSocket update broadcast for task {task_id}")
                    except Exception as ws_error:
                        logger.warning(f"Failed to broadcast WebSocket update: {ws_error}")
            
                return json.dumps({
                    "success": True,
                    "task": task
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Task {task_id} not found"
                })
            
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            return json.dumps({
                "success": False,
                "error": f"Error updating task status: {str(e)}"
            }) 
