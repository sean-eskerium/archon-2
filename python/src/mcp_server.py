"""
# TODO: Add robust error handling, connection pooling for external services, health check endpoints, circuit breaker pattern, and resource optimization.
# Example: Use tenacity for retries, implement /health endpoint, and wrap external calls with circuit breaker logic.
Modular MCP Server for Archon

This is the main MCP server that coordinates multiple tool modules:
- RAG Module: Web crawling, document storage, and retrieval
- Tasks Module: Project and task management
- Future UI Module: Agent-UI integration

Each module registers its tools with this shared FastMCP instance.

Enhanced with comprehensive error handling, logging, and robustness features.
"""
from mcp.server.fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Optional
from sentence_transformers import CrossEncoder
from dotenv import load_dotenv
from supabase import Client
from pathlib import Path
import os
import sys
import asyncio
import logging
import traceback
import time
from datetime import datetime
import threading

from crawl4ai import AsyncWebCrawler, BrowserConfig

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables from the project root .env file
project_root = Path(__file__).resolve().parent.parent
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path, override=True)

# Configure logging FIRST before any imports that might use it
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/mcp_server.log', mode='a') if os.path.exists('/tmp') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import Logfire configuration
from src.logfire_config import setup_logfire, mcp_logger

# Import session management (after path setup)
from src.services.mcp_session_manager import get_session_manager

try:
    from src.utils import get_supabase_client
except ImportError as e:
    logger.error(f"Failed to import utils: {e}")
    raise

# Global initialization lock and flag
_initialization_lock = threading.Lock()
_initialization_complete = False
_shared_context = None

@dataclass
class ArchonContext:
    """
    Shared context for all Archon MCP modules.
    
    This context holds resources that can be used by any module:
    - AsyncWebCrawler for web operations
    - Supabase client for database operations  
    - Optional reranking model for search enhancement
    """
    crawler: AsyncWebCrawler
    supabase_client: Client
    reranking_model: Optional[CrossEncoder] = None
    health_status: dict = None
    startup_time: float = None

    def __post_init__(self):
        if self.health_status is None:
            self.health_status = {
                "status": "healthy",
                "crawler_ready": False,
                "database_ready": False,
                "reranking_ready": False,
                "last_health_check": None
            }
        if self.startup_time is None:
            self.startup_time = time.time()

def check_supabase_health(client: Client) -> bool:
    """Check if Supabase is accessible."""
    try:
        # Try a simple query to test connection
        response = client.table("settings").select("key").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        return False

def check_crawler_health(crawler: AsyncWebCrawler) -> bool:
    """Check if crawler is ready."""
    try:
        # Simple check to see if crawler is initialized
        return hasattr(crawler, 'config') and crawler.config is not None
    except Exception as e:
        logger.error(f"Crawler health check failed: {e}")
        return False

async def perform_health_checks(context: ArchonContext):
    """Perform comprehensive health checks on all services."""
    try:
        # Check database
        context.health_status["database_ready"] = check_supabase_health(context.supabase_client)
        
        # Check crawler
        context.health_status["crawler_ready"] = check_crawler_health(context.crawler)
        
        # Check reranking model
        context.health_status["reranking_ready"] = context.reranking_model is not None
        
        # Overall status
        all_critical_ready = (
            context.health_status["database_ready"] and 
            context.health_status["crawler_ready"]
        )
        
        context.health_status["status"] = "healthy" if all_critical_ready else "degraded"
        context.health_status["last_health_check"] = datetime.now().isoformat()
        
        if not all_critical_ready:
            logger.warning(f"Health check failed: {context.health_status}")
        else:
            logger.info("Health check passed - all services healthy")
            
    except Exception as e:
        logger.error(f"Health check error: {e}")
        context.health_status["status"] = "unhealthy"
        context.health_status["last_health_check"] = datetime.now().isoformat()

@asynccontextmanager
async def archon_lifespan(server: FastMCP) -> AsyncIterator[ArchonContext]:
    """
    Manages the shared resources lifecycle with proper initialization.
    Following official MCP patterns from the Python SDK documentation.
    
    Now with singleton pattern to prevent duplicate initialization on multiple SSE connections.
    """
    global _initialization_complete, _shared_context
    
    # Quick check without lock
    if _initialization_complete and _shared_context:
        logger.info("♻️ Reusing existing Archon context for new SSE connection")
        yield _shared_context
        return
    
    # Acquire lock for initialization
    with _initialization_lock:
        # Double-check pattern
        if _initialization_complete and _shared_context:
            logger.info("♻️ Reusing existing Archon context for new SSE connection")
            yield _shared_context
            return
        
        logger.info("🚀 Starting Archon MCP server lifespan...")
        
        # Check OpenAI API key availability (should be set by FastAPI startup)
        openai_key_available = bool(os.getenv("OPENAI_API_KEY"))
        logger.info(f"🔑 OpenAI API key status: {'AVAILABLE' if openai_key_available else 'NOT FOUND'}")
        
        # Initialize resources needed for full operation
        crawler = None
        supabase_client = None
        reranking_model = None
        
        try:
            # Initialize session manager (no longer needs async start)
            logger.info("🔐 Initializing session manager...")
            session_manager = get_session_manager()
            logger.info("✓ Session manager initialized")
            # Initialize essential services
            logger.info("🗄️ Initializing Supabase client...")
            supabase_client = get_supabase_client()
            logger.info("✓ Supabase client initialized")
            
            # Initialize AsyncWebCrawler if available
            logger.info("🕷️ Initializing web crawler...")
            try:
                browser_config = BrowserConfig(
                    headless=True,
                    verbose=False
                )
                crawler = AsyncWebCrawler(config=browser_config)
                await crawler.__aenter__()
                logger.info("✓ Web crawler initialized")
            except Exception as e:
                logger.warning(f"⚠ Failed to initialize web crawler: {e}")
                crawler = None
            
            # Initialize reranking model if enabled
            use_reranking = os.getenv("USE_RERANKING", "false").lower() == "true"
            if use_reranking:
                logger.info("🧠 Initializing reranking model...")
                try:
                    reranking_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
                    logger.info("✓ Reranking model initialized")
                except Exception as e:
                    logger.warning(f"⚠ Failed to initialize reranking model: {e}")
                    reranking_model = None
            else:
                logger.info("⚠ Reranking disabled - skipping model initialization")
            
            # Create context  
            context = ArchonContext(
                crawler=crawler,
                supabase_client=supabase_client,
                reranking_model=reranking_model
            )
            
            # Set ready status based on actual initialization
            context.health_status["database_ready"] = supabase_client is not None
            context.health_status["crawler_ready"] = crawler is not None
            context.health_status["reranking_ready"] = reranking_model is not None
            context.health_status["openai_key_available"] = openai_key_available
            context.health_status["last_health_check"] = datetime.now().isoformat()
            
            # Overall status: healthy if database is ready, degraded if crawler missing, unhealthy if database missing
            if not context.health_status["database_ready"]:
                context.health_status["status"] = "unhealthy"
            elif not context.health_status["crawler_ready"]:
                context.health_status["status"] = "degraded"
            else:
                context.health_status["status"] = "healthy"
            
            logger.info("✓ Archon context ready - server can accept requests")
            
            # Store context globally
            _shared_context = context
            _initialization_complete = True
            
            yield context
            
        except Exception as e:
            logger.error(f"💥 Critical error in lifespan setup: {e}")
            logger.error(traceback.format_exc())
            raise
        finally:
            # Clean up resources  
            logger.info("🧹 Cleaning up Archon resources...")
            try:
                if crawler:
                    await crawler.__aexit__(None, None, None)
                    logger.info("✓ Crawler cleaned up")
            except Exception as e:
                logger.error(f"✗ Error cleaning up crawler: {e}")
            
            # Session manager cleanup is now handled by SimplifiedSessionManager
            logger.info("✓ Session manager cleanup complete")
            
            logger.info("✅ Archon MCP server lifespan ended")

# Initialize the main FastMCP server with fixed configuration
try:
    # Fixed configuration for SSE-only mode
    server_host = "0.0.0.0"  # Listen on all interfaces
    server_port = 8051       # Fixed port
    
    logger.info("🏗️ FASTMCP SERVER INITIALIZATION:")
    logger.info(f"   Server Name: archon-mcp-server")
    logger.info(f"   Description: Modular MCP server for Archon: RAG, Tasks, and UI tools")
    logger.info(f"   Host: {server_host}")
    logger.info(f"   Port: {server_port}")
    logger.info(f"   Mode: SSE-only")
    
    mcp = FastMCP(
        "archon-mcp-server",
        description="Modular MCP server for Archon: RAG, Tasks, and UI tools",
        lifespan=archon_lifespan,
        host=server_host,
        port=server_port
    )
    logger.info(f"✓ FastMCP server instance created successfully")
    logger.info(f"   SSE endpoint: http://{server_host}:{server_port}/sse")
    logger.info(f"   Compatible with: Windsurf, Cursor, Claude Code")
    
except Exception as e:
    logger.error(f"✗ Failed to create FastMCP server: {e}")
    logger.error(traceback.format_exc())
    raise

# Health check endpoint
@mcp.tool()
async def health_check(ctx: Context) -> str:
    """
    Perform a lightweight health check that can respond immediately.
    
    Returns:
        JSON string with current health status
    """
    import json
    
    try:
        # Try to get the lifespan context (may not be ready during startup)
        context = getattr(ctx.request_context, 'lifespan_context', None)
        
        if context is None:
            # Server starting up - return basic status
            return json.dumps({
                "success": True,
                "status": "starting",
                "message": "MCP server is initializing...",
                "timestamp": datetime.now().isoformat()
            })
        
        # Server is ready - return full health status
        if hasattr(context, 'health_status') and context.health_status:
            # Perform quick health checks without blocking
            await perform_health_checks(context)
            
            return json.dumps({
                "success": True,
                "health": context.health_status,
                "uptime_seconds": time.time() - context.startup_time,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return json.dumps({
                "success": True,
                "status": "ready",
                "message": "MCP server is running",
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        # Always return something - never crash
        return json.dumps({
            "success": False,
            "error": f"Health check failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

# Session management endpoint
@mcp.tool()
async def session_info(ctx: Context) -> str:
    """
    Get information about the current session and all active sessions.
    
    This tool helps debug session management and connection issues.
    
    Returns:
        JSON string with session information
    """
    import json
    
    try:
        session_manager = get_session_manager()
        
        # Build session info
        session_info_data = {
            'active_sessions': session_manager.get_active_session_count(),
            'session_timeout': session_manager.timeout
        }
        
        # Add server uptime
        context = getattr(ctx.request_context, 'lifespan_context', None)
        if context and hasattr(context, 'startup_time'):
            session_info_data['server_uptime_seconds'] = time.time() - context.startup_time
        
        return json.dumps({
            "success": True,
            "session_management": session_info_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Session info failed: {e}")
        return json.dumps({
            "success": False,
            "error": f"Failed to get session info: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

# Session Management Integration
# Note: FastMCP handles the MCP protocol internally, including initialization.
# For session management, we rely on the MCP specification where:
# 1. Server returns Mcp-Session-Id header in InitializeResponse
# 2. Client includes this header in subsequent requests
# 3. Server returns 404 when session expires
# This is handled by FastMCP's internal SSE implementation.

# Import and register all modules
def register_modules():
    """Register all MCP tool modules with the main server."""
    logger.info("🔧 Registering MCP tool modules...")
    
    modules_registered = 0
    
    # Import and register RAG module
    try:
        from src.modules.rag_module import register_rag_tools
        register_rag_tools(mcp)
        modules_registered += 1
        logger.info("✓ RAG module registered")
    except ImportError as e:
        logger.warning(f"⚠ RAG module not available: {e}")
    except Exception as e:
        logger.error(f"✗ Error registering RAG module: {e}")
        logger.error(traceback.format_exc())
    
    # Import and register Project module - only if Projects are enabled
    projects_enabled = os.getenv("PROJECTS_ENABLED", "true").lower() == "true"
    if projects_enabled:
        try:
            from src.modules.project_module import register_project_tools
            register_project_tools(mcp)
            modules_registered += 1
            logger.info("✓ Project module registered (5 consolidated tools)")
        except ImportError as e:
            logger.warning(f"⚠ Project module not available: {e}")
        except Exception as e:
            logger.error(f"✗ Error registering Project module: {e}")
            logger.error(traceback.format_exc())
    else:
        logger.info("⚠ Project module skipped - Projects are disabled")
    
    # Versioning is now integrated into the project module
    
    # Future UI module will be added here
    # try:
    #     from src.modules.ui_module import register_ui_tools
    #     register_ui_tools(mcp)
    #     modules_registered += 1
    #     logger.info("✓ UI module registered") 
    # except ImportError as e:
    #     logger.warning(f"⚠ UI module not available: {e}")
    # except Exception as e:
    #     logger.error(f"✗ Error registering UI module: {e}")
    
    logger.info(f"📦 Total modules registered: {modules_registered}")
    
    if modules_registered == 0:
        logger.error("💥 No modules were successfully registered!")
        raise RuntimeError("No MCP modules available")

# Register all modules when this file is imported
try:
    register_modules()
except Exception as e:
    logger.error(f"💥 Critical error during module registration: {e}")
    logger.error(traceback.format_exc())
    raise

async def main():
    """Main entry point for the MCP server - SSE mode only."""
    try:
        # Initialize Logfire first
        setup_logfire(service_name="archon-mcp-server")
        
        # Fixed configuration for SSE-only mode
        host = "0.0.0.0"  # Listen on all interfaces
        port = 8051      # Fixed port
        
        logger.info("🚀 Starting Archon MCP Server")
        logger.info(f"   Mode: SSE-only")
        logger.info(f"   Host: {host}")
        logger.info(f"   Port: {port}")
        logger.info(f"   URL: http://{host}:{port}/sse")
        
        mcp_logger.info("🔥 Logfire initialized for MCP server")
        mcp_logger.info("🌟 Starting Archon MCP server in SSE mode", host=host, port=port)
        
        # Run SSE server
        logger.info("🌐 Starting Server-Sent Events (SSE) transport")
        logger.info(f"   SSE endpoint: http://{host}:{port}/sse")
        logger.info(f"   WebSocket endpoint: ws://{host}:{port}/ws")
        logger.info("   Connect from Windsurf, Cursor, or Claude Code using the SSE endpoint")
        
        mcp_logger.info("🌐 SSE server starting", url=f"http://{host}:{port}/sse")
        await mcp.run_sse_async()
            
    except Exception as e:
        mcp_logger.error("💥 Fatal error in main", error=str(e), error_type=type(e).__name__)
        logger.error(f"💥 Fatal error in main: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Archon MCP server stopped by user")
    except Exception as e:
        logger.error(f"💥 Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) 
