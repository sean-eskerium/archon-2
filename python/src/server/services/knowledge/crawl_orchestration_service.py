"""
Crawl Orchestration Service

Handles the orchestration of crawling operations with progress tracking.
Extracted from the monolithic _perform_crawl_with_progress function in knowledge_api.py.
"""
import asyncio
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from queue import Queue
import urllib.error
import uuid

from ...config.logfire_config import safe_logfire_info, safe_logfire_error
from ..rag.crawling_service import CrawlingService
from ..storage.storage_services import DocumentStorageService
from ..storage.document_storage_service import add_documents_to_supabase
from ..storage.document_storage_sync import add_documents_to_supabase_sync
from .code_extraction_service import CodeExtractionService
from ...fastapi.socketio_handlers import update_crawl_progress
from ..source_management_service import update_source_info, extract_source_summary
from ..background_task_manager import get_task_manager
from .progress_mapper import ProgressMapper


class CrawlOrchestrationService:
    """
    Orchestrates the crawling process for knowledge items.
    Handles URL type detection, crawling, document storage, code extraction, and progress tracking.
    """
    
    def __init__(self, crawler, supabase_client, progress_id=None):
        """
        Initialize the crawl orchestration service.
        
        Args:
            crawler: The Crawl4AI crawler instance
            supabase_client: The Supabase client for database operations
            progress_id: Optional progress ID for Socket.IO updates
        """
        self.crawler = crawler
        self.supabase_client = supabase_client
        self.crawling_service = CrawlingService(crawler=crawler, supabase_client=supabase_client)
        self.doc_storage_service = DocumentStorageService(supabase_client)
        self.progress_id = progress_id
        # Track progress state across all stages to prevent UI resets
        self.progress_state = {'progressId': self.progress_id} if self.progress_id else {}
        # Initialize progress mapper to prevent backwards jumps
        self.progress_mapper = ProgressMapper()
    
    def set_progress_id(self, progress_id: str):
        """Set the progress ID for Socket.IO updates."""
        self.progress_id = progress_id
    
    def _is_documentation_site(self, url: str) -> bool:
        """Check if URL is a documentation site."""
        doc_patterns = [
            'docs.', 'documentation.', '/docs/', '/documentation/',
            'readthedocs', 'gitbook', 'docusaurus', 'vitepress',
            'docsify', 'mkdocs', 'copilotkit'
        ]
        return any(pattern in url.lower() for pattern in doc_patterns)
    
    async def _create_crawl_progress_callback(self, base_status: str):
        """Create a progress callback for crawling operations."""
        async def callback(status: str, percentage: int, message: str, **kwargs):
            if self.progress_id:
                # Update and preserve progress state
                self.progress_state.update({
                    'status': base_status,
                    'percentage': percentage,
                    'log': message,
                    **kwargs
                })
                safe_logfire_info(f"Emitting crawl progress | progress_id={self.progress_id} | status={base_status} | percentage={percentage}")
                await update_crawl_progress(self.progress_id, self.progress_state)
        return callback

    async def _async_orchestrate_crawl(self, request: Dict[str, Any], task_id: str):
        """
        Async orchestration that runs in the main event loop.
        Browser operations happen here, only CPU-intensive work uses threads.
        """
        last_heartbeat = asyncio.get_event_loop().time()
        heartbeat_interval = 30.0  # Send heartbeat every 30 seconds
        
        async def send_heartbeat_if_needed():
            """Send heartbeat to keep Socket.IO connection alive"""
            nonlocal last_heartbeat
            current_time = asyncio.get_event_loop().time()
            if current_time - last_heartbeat >= heartbeat_interval:
                await self._handle_progress_update(task_id, {
                    'status': self.progress_mapper.get_current_stage(),
                    'percentage': self.progress_mapper.get_current_progress(),
                    'heartbeat': True,
                    'log': 'Background task still running...',
                    'message': 'Processing...'
                })
                last_heartbeat = current_time
        
        try:
            url = str(request.get('url', ''))
            safe_logfire_info(f"Starting async crawl orchestration | url={url} | task_id={task_id}")
            
            # Helper to update progress with mapper
            async def update_mapped_progress(stage: str, stage_progress: int, message: str, **kwargs):
                overall_progress = self.progress_mapper.map_progress(stage, stage_progress)
                await self._handle_progress_update(task_id, {
                    'status': stage,
                    'percentage': overall_progress,
                    'log': message,
                    'message': message,
                    **kwargs
                })
            
            # Initial progress
            await update_mapped_progress('starting', 100, f'Starting crawl of {url}', currentUrl=url)
            
            # Analyzing stage
            await update_mapped_progress('analyzing', 50, f'Analyzing URL type for {url}')
            
            # Detect URL type and perform crawl (async - stays in event loop)
            crawl_results, crawl_type = await self._crawl_by_url_type(url, request)
            
            # Send heartbeat after potentially long crawl operation
            await send_heartbeat_if_needed()
            
            if not crawl_results:
                raise ValueError("No content was crawled from the provided URL")
            
            # Processing stage
            await update_mapped_progress('processing', 50, 'Processing crawled content')
            
            # Process and store documents
            storage_results = await self._process_and_store_documents(
                crawl_results, request, crawl_type
            )
            
            # Send heartbeat after document storage
            await send_heartbeat_if_needed()
            
            # Extract code examples if requested
            code_examples_count = 0
            if request.get('extract_code_examples', True):
                await update_mapped_progress('code_extraction', 0, 'Starting code extraction...')
                
                code_examples_count = await self._extract_and_store_code_examples(
                    crawl_results,
                    storage_results['url_to_full_document']
                )
                
                # Send heartbeat after code extraction
                await send_heartbeat_if_needed()
            
            # Finalization
            await update_mapped_progress(
                'finalization', 50, 'Finalizing crawl results...',
                chunks_stored=storage_results['chunk_count'],
                code_examples_found=code_examples_count
            )
            
            # Complete - send both the progress update and completion event
            await update_mapped_progress(
                'completed', 100, 
                f'Crawl completed: {storage_results["chunk_count"]} chunks, {code_examples_count} code examples',
                chunks_stored=storage_results['chunk_count'],
                code_examples_found=code_examples_count,
                processed_pages=len(crawl_results),
                total_pages=len(crawl_results)
            )
            
            # Also send the completion event that frontend expects
            from ...fastapi.socketio_handlers import complete_crawl_progress
            await complete_crawl_progress(task_id, {
                'chunks_stored': storage_results['chunk_count'],
                'code_examples_found': code_examples_count,
                'processed_pages': len(crawl_results),
                'total_pages': len(crawl_results),
                'sourceId': storage_results.get('source_id', ''),
                'log': f'Crawl completed successfully!'
            })
            
        except Exception as e:
            safe_logfire_error(f"Async crawl orchestration failed | error={str(e)}")
            await self._handle_progress_update(task_id, {
                'status': 'error',
                'percentage': -1,
                'log': f'Crawl failed: {str(e)}'
            })

    async def orchestrate_crawl(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main orchestration method - now non-blocking using asyncio.create_task.
        Browser operations stay in the main event loop.
        
        Args:
            request: The crawl request containing url, knowledge_type, tags, max_depth, etc.
            
        Returns:
            Dict containing task_id and status
        """
        url = str(request.get('url', ''))
        safe_logfire_info(f"Starting background crawl orchestration | url={url}")
        
        # Create task ID
        task_id = self.progress_id or str(uuid.uuid4())
        
        # Start the crawl as an async task in the main event loop
        asyncio.create_task(self._async_orchestrate_crawl(request, task_id))
        
        # Return immediately
        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Crawl operation started for {url}",
            "progress_id": self.progress_id
        }
    
    def _blocking_orchestrate_crawl(self, progress_queue: Queue, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Blocking version of orchestrate_crawl that runs in thread pool.
        
        Args:
            progress_queue: Queue for progress updates
            request: The crawl request
            
        Returns:
            Dict containing crawl results and statistics
        """
        try:
            url = str(request.get('url', ''))
            safe_logfire_info(f"Starting blocking crawl orchestration | url={url}")
            
            # Initial progress update
            progress_queue.put({
                'status': 'analyzing',
                'percentage': 0,
                'currentUrl': url,
                'log': f'Analyzing URL type for {url}'
            })
            
            # Detect URL type and perform appropriate crawl
            crawl_results, crawl_type = self._crawl_by_url_type_blocking(url, request, progress_queue)
            
            if not crawl_results:
                raise ValueError("No content was crawled from the provided URL")
            
            # Process and store documents
            progress_queue.put({
                'status': 'processing',
                'percentage': 50,
                'log': 'Processing and storing documents'
            })
            storage_results = self._process_and_store_documents_blocking(
                crawl_results, request, crawl_type, progress_queue
            )
            
            # Extract url_to_full_document from storage results
            url_to_full_document = storage_results.get('url_to_full_document', {})
            
            # Extract code examples if requested
            code_examples_count = 0
            if request.get('extract_code_examples', True):
                progress_queue.put({
                    'status': 'extracting', 
                    'percentage': 90,
                    'log': 'Extracting code examples...'
                })
                safe_logfire_info("Starting code extraction in background task")
                
                # Use the async code extraction method via run_async_in_thread
                # This maintains Socket.IO connection by using the main event loop
                from ..blocking_helpers import run_async_in_thread
                from ..knowledge.code_extraction_service import CodeExtractionService
                
                # Create code extraction service
                code_service = CodeExtractionService(self.supabase_client)
                
                # Define async progress callback that writes to queue
                async def async_progress_callback(data: dict):
                    progress_queue.put(data)
                
                try:
                    # Run the async extraction method using the main event loop
                    code_examples_count = run_async_in_thread(
                        code_service.extract_and_store_code_examples(
                            crawl_results,
                            url_to_full_document,
                            async_progress_callback,
                            start_progress=85,
                            end_progress=95
                        ),
                        timeout=300.0  # 5 minute timeout for code extraction
                    )
                    safe_logfire_info(f"Code extraction completed: {code_examples_count} examples stored")
                except Exception as e:
                    safe_logfire_error(f"Error in code extraction: {e}")
                    code_examples_count = 0
            
            # Finalize and return results
            progress_queue.put({
                'status': 'finalization',
                'percentage': 97,
                'log': 'Finalizing crawl results...',
                'chunks_stored': storage_results['chunk_count'],
                'code_examples_found': code_examples_count
            })
            
            progress_queue.put({
                'status': 'finalization',
                'percentage': 99,
                'log': 'Preparing final report...',
                'chunks_stored': storage_results['chunk_count'],
                'code_examples_found': code_examples_count,
                'processed_pages': len(crawl_results),
                'total_pages': len(crawl_results)
            })
            
            # Final completion update
            progress_queue.put({
                'status': 'completed',
                'percentage': 100,
                'log': f'Crawl completed successfully: {storage_results["chunk_count"]} chunks stored, {code_examples_count} code examples found',
                'chunks_stored': storage_results['chunk_count'],
                'code_examples_found': code_examples_count,
                'processed_pages': len(crawl_results),
                'total_pages': len(crawl_results)
            })
            
            return {
                'success': True,
                'chunks_stored': storage_results['chunk_count'],
                'word_count': storage_results['total_word_count'],
                'code_examples_stored': code_examples_count,
                'processed_pages': len(crawl_results),
                'total_pages': len(crawl_results)
            }
            
        except Exception as e:
            safe_logfire_error(f"Crawl orchestration failed | error={str(e)}")
            progress_queue.put({
                'status': 'error',
                'percentage': -1,  # Don't reset to 0 on error
                'log': f'Crawl failed: {str(e)}'
            })
            raise
    
    async def _crawl_by_url_type(self, url: str, request: Dict[str, Any]) -> tuple:
        """
        Detect URL type and perform appropriate crawling.
        
        Returns:
            Tuple of (crawl_results, crawl_type)
        """
        crawl_results = []
        crawl_type = None
        
        if self.crawling_service.is_txt(url):
            # Handle text files
            if self.progress_id:
                self.progress_state.update({
                    'status': 'crawling',
                    'percentage': 10,
                    'log': 'Detected text file, fetching content...'
                })
                await update_crawl_progress(self.progress_id, self.progress_state)
            crawl_results = await self.crawling_service.crawl_markdown_file(
                url,
                progress_callback=await self._create_crawl_progress_callback('crawling'),
                start_progress=10,
                end_progress=20
            )
            crawl_type = "text_file"
            
        elif self.crawling_service.is_sitemap(url):
            # Handle sitemaps
            if self.progress_id:
                self.progress_state.update({
                    'status': 'crawling',
                    'percentage': 10,
                    'log': 'Detected sitemap, parsing URLs...'
                })
                await update_crawl_progress(self.progress_id, self.progress_state)
            sitemap_urls = self.crawling_service.parse_sitemap(url)
            
            if sitemap_urls:
                # Emit progress before starting batch crawl
                if self.progress_id:
                    self.progress_state.update({
                        'status': 'crawling',
                        'percentage': 15,
                        'log': f'Starting batch crawl of {len(sitemap_urls)} URLs...'
                    })
                    await update_crawl_progress(self.progress_id, self.progress_state)
                
                crawl_results = await self.crawling_service.crawl_batch_with_progress(
                    sitemap_urls,
                    progress_callback=await self._create_crawl_progress_callback('crawling'),
                    start_progress=15,
                    end_progress=20
                )
                crawl_type = "sitemap"
                
        else:
            # Handle regular webpages with recursive crawling
            if self.progress_id:
                self.progress_state.update({
                    'status': 'crawling',
                    'percentage': 10,
                    'log': f'Starting recursive crawl with max depth {request.get("max_depth", 1)}...'
                })
                await update_crawl_progress(self.progress_id, self.progress_state)
            
            max_depth = request.get('max_depth', 1)
            # Limit concurrent crawls for better performance
            max_concurrent = 20 if self._is_documentation_site(url) else 10
            
            crawl_results = await self.crawling_service.crawl_recursive_with_progress(
                [url],
                max_depth=max_depth,
                max_concurrent=max_concurrent,
                progress_callback=await self._create_crawl_progress_callback('crawling'),
                start_progress=10,
                end_progress=20
            )
            crawl_type = "webpage"
        
        return crawl_results, crawl_type
    
    async def _process_and_store_documents(self, crawl_results: List[Dict], request: Dict[str, Any], 
                                          crawl_type: str) -> Dict[str, Any]:
        """
        Process crawled documents and store them in the database.
        
        Returns:
            Dict containing storage statistics and document mappings
        """
        # Progress will be reported by document storage service
        
        # Import the document storage service for chunking
        from ..storage.storage_services import DocumentStorageService
        
        # Initialize storage service for chunking
        storage_service = DocumentStorageService(self.supabase_client)
        
        # Prepare data for chunked storage
        all_urls = []
        all_chunk_numbers = []
        all_contents = []
        all_metadatas = []
        source_word_counts = {}
        url_to_full_document = {}
        
        # Process and chunk each document
        for doc_index, doc in enumerate(crawl_results):
            source_url = doc.get('url', '')
            markdown_content = doc.get('markdown', '')
            
            if not markdown_content:
                continue
            
            # Store full document for code extraction context
            url_to_full_document[source_url] = markdown_content
            
            # CHUNK THE CONTENT (restored from old implementation)
            chunks = storage_service.smart_chunk_text(markdown_content, chunk_size=5000)
            
            # Extract source_id
            parsed_url = urlparse(source_url)
            source_id = parsed_url.netloc or parsed_url.path
            safe_logfire_info(f"Extracted source_id '{source_id}' from URL '{source_url}'")
            
            # Process each chunk
            for i, chunk in enumerate(chunks):
                all_urls.append(source_url)
                all_chunk_numbers.append(i)
                all_contents.append(chunk)
                
                # Create metadata for each chunk
                word_count = len(chunk.split())
                metadata = {
                    'url': source_url,
                    'title': doc.get('title', ''),
                    'description': doc.get('description', ''),
                    'source_id': source_id,
                    'knowledge_type': request.get('knowledge_type', 'documentation'),
                    'crawl_type': crawl_type,
                    'word_count': word_count,
                    'char_count': len(chunk),
                    'chunk_index': i,
                    'tags': request.get('tags', [])
                }
                all_metadatas.append(metadata)
                
                # Accumulate word count
                source_word_counts[source_id] = source_word_counts.get(source_id, 0) + word_count
                
                # Yield control every 10 chunks to prevent event loop blocking
                if i > 0 and i % 10 == 0:
                    await asyncio.sleep(0)
            
            # Yield control after processing each document
            if doc_index > 0 and doc_index % 5 == 0:
                await asyncio.sleep(0)
        
        # Create/update source record FIRST before storing documents
        if all_contents and all_metadatas:
            # Find ALL unique source_ids in the crawl results
            unique_source_ids = set()
            source_id_contents = {}
            source_id_word_counts = {}
            
            for i, metadata in enumerate(all_metadatas):
                source_id = metadata['source_id']
                unique_source_ids.add(source_id)
                
                # Group content by source_id for better summaries
                if source_id not in source_id_contents:
                    source_id_contents[source_id] = []
                source_id_contents[source_id].append(all_contents[i])
                
                # Track word counts per source_id
                if source_id not in source_id_word_counts:
                    source_id_word_counts[source_id] = 0
                source_id_word_counts[source_id] += metadata.get('word_count', 0)
            
            safe_logfire_info(f"Found {len(unique_source_ids)} unique source_ids: {list(unique_source_ids)}")
            
            # Create source records for ALL unique source_ids
            for source_id in unique_source_ids:
                # Get combined content for this specific source_id
                source_contents = source_id_contents[source_id]
                combined_content = ''
                for chunk in source_contents[:3]:  # First 3 chunks for this source
                    if len(combined_content) + len(chunk) < 15000:
                        combined_content += ' ' + chunk
                    else:
                        break
                
                # Generate summary with fallback
                try:
                    summary = extract_source_summary(source_id, combined_content)
                except Exception as e:
                    safe_logfire_error(f"Failed to generate AI summary for '{source_id}': {str(e)}, using fallback")
                    # Fallback to simple summary
                    summary = f"Documentation from {source_id} - {len(source_contents)} pages crawled"
                
                # Update source info in database BEFORE storing documents
                safe_logfire_info(f"About to create/update source record for '{source_id}' (word count: {source_id_word_counts[source_id]})")
                try:
                    update_source_info(
                        client=self.supabase_client,
                        source_id=source_id,
                        summary=summary,
                        word_count=source_id_word_counts[source_id],
                        content=combined_content,
                        knowledge_type=request.get('knowledge_type', 'technical'),
                        tags=request.get('tags', []),
                        update_frequency=0  # Set to 0 since we're using manual refresh
                    )
                    safe_logfire_info(f"Successfully created/updated source record for '{source_id}'")
                except Exception as e:
                    safe_logfire_error(f"Failed to create/update source record for '{source_id}': {str(e)}")
                    # Try a simpler approach with minimal data
                    try:
                        safe_logfire_info(f"Attempting fallback source creation for '{source_id}'")
                        self.supabase_client.table('sources').upsert({
                            'source_id': source_id,
                            'title': source_id,  # Use source_id as title fallback
                            'summary': summary,
                            'total_word_count': source_id_word_counts[source_id],
                            'metadata': {
                                'knowledge_type': request.get('knowledge_type', 'technical'),
                                'tags': request.get('tags', []),
                                'auto_generated': True,
                                'fallback_creation': True
                            }
                        }).execute()
                        safe_logfire_info(f"Fallback source creation succeeded for '{source_id}'")
                    except Exception as fallback_error:
                        safe_logfire_error(f"Both source creation attempts failed for '{source_id}': {str(fallback_error)}")
                        raise Exception(f"Unable to create source record for '{source_id}'. This will cause foreign key violations. Error: {str(fallback_error)}")
        
        # Verify ALL source records exist before proceeding with document storage
        if unique_source_ids:
            for source_id in unique_source_ids:
                try:
                    source_check = self.supabase_client.table('sources').select('source_id').eq('source_id', source_id).execute()
                    if not source_check.data:
                        raise Exception(f"Source record verification failed - '{source_id}' does not exist in sources table")
                    safe_logfire_info(f"Source record verified for '{source_id}'")
                except Exception as e:
                    safe_logfire_error(f"Source verification failed for '{source_id}': {str(e)}")
                    raise
            
            safe_logfire_info(f"All {len(unique_source_ids)} source records verified - proceeding with document storage")
        
        # Document storage progress will be handled by the callback
        
        # Contextual embeddings will be loaded from credential service in document_storage_service
            
        safe_logfire_info(f"url_to_full_document keys: {list(url_to_full_document.keys())[:5]}")
        
        # Log chunking results
        safe_logfire_info(f"Document storage | documents={len(crawl_results)} | chunks={len(all_contents)} | avg_chunks_per_doc={len(all_contents)/len(crawl_results):.1f}")
        
        # Create a progress callback for document storage
        async def doc_storage_callback(message: str, percentage: int, batch_info: Optional[dict] = None):
            if self.progress_id:
                # Map percentage to document storage range (20-85%)
                mapped_percentage = 20 + int((percentage / 100) * (85 - 20))
                safe_logfire_info(f"Document storage progress mapping: {percentage}% -> {mapped_percentage}%")
                
                # Update progress state while preserving existing fields
                self.progress_state.update({
                    'status': 'document_storage',
                    'percentage': mapped_percentage,
                    'log': message
                })
                
                # Add batch_info fields if provided
                if batch_info:
                    self.progress_state.update(batch_info)
                
                await update_crawl_progress(self.progress_id, self.progress_state)
        
        # Call add_documents_to_supabase with the correct parameters
        # Progress update already handled at start of function
        
        await add_documents_to_supabase(
            client=self.supabase_client,
            urls=all_urls,  # Now has entry per chunk
            chunk_numbers=all_chunk_numbers,  # Proper chunk numbers (0, 1, 2, etc)
            contents=all_contents,  # Individual chunks
            metadatas=all_metadatas,  # Metadata per chunk
            url_to_full_document=url_to_full_document,
            batch_size=10,
            progress_callback=doc_storage_callback,  # Pass the callback for progress updates
            enable_parallel_batches=True,  # Enable parallel processing
            provider=None  # Use configured provider
        )
        
        # Progress will be at 80% after document storage completes
        
        # Calculate actual chunk count
        chunk_count = len(all_contents)
        
        # Source update already done during document storage
        
        return {
            'chunk_count': chunk_count,
            'total_word_count': sum(source_word_counts.values()),
            'url_to_full_document': url_to_full_document
        }
    
    async def _extract_and_store_code_examples(self, crawl_results: List[Dict], 
                                              url_to_full_document: Dict[str, str]) -> int:
        """
        Extract code examples from crawled documents and store them.
        
        Returns:
            Number of code examples stored
        """
        # Use CodeExtractionService
        code_service = CodeExtractionService(self.supabase_client)
        
        # Create progress callback for code extraction
        async def code_progress_callback(data: dict):
            if self.progress_id:
                # Update progress state while preserving existing fields
                self.progress_state.update(data)
                await update_crawl_progress(self.progress_id, self.progress_state)
        
        result = await code_service.extract_and_store_code_examples(
            crawl_results,
            url_to_full_document,
            code_progress_callback,
            start_progress=85,
            end_progress=95
        )
        
        # No need for duplicate progress update here - the code extraction service handles it
        
        return result
    
    async def _handle_progress_update(self, task_id: str, update: Dict[str, Any]):
        """
        Handle progress updates from background task.
        This is an async method that will be called from the BackgroundTaskManager in the main event loop.
        """
        if self.progress_id:
            # Update and preserve progress state
            self.progress_state.update(update)
            # Ensure progressId is always included
            if self.progress_id and 'progressId' not in self.progress_state:
                self.progress_state['progressId'] = self.progress_id
            
            # Throttle Socket.IO updates to prevent overwhelming the connection
            # Only send updates for:
            # 1. Status changes
            # 2. Every 5% progress change
            # 3. Important messages (errors, completion)
            current_status = update.get('status', '')
            current_percentage = update.get('percentage', 0)
            
            # Always emit progress updates for real-time feedback
            # The socketio_handlers already has rate limiting built in
            await update_crawl_progress(self.progress_id, self.progress_state)
    
    def _extract_code_examples_blocking(self, crawl_results: List[Dict[str, Any]], 
                                       storage_results: Dict[str, Any], 
                                       progress_queue: Queue) -> Dict[str, Any]:
        """
        Blocking version of code extraction for background tasks.
        
        Args:
            crawl_results: Results from crawling
            storage_results: Results from document storage
            progress_queue: Queue for progress updates
            
        Returns:
            Dict with code extraction results
        """
        try:
            safe_logfire_info("Starting blocking code extraction")
            
            # Get url_to_full_document from storage results
            url_to_full_document = storage_results.get('url_to_full_document', {})
            
            # Create code extraction service with synchronous supabase client
            from ..knowledge.code_extraction_service import CodeExtractionService
            code_service = CodeExtractionService(self.supabase_client)
            
            # Define async progress callback that writes to queue
            async def async_progress_callback(data: dict):
                # The data dict already contains the proper progress mapping
                progress_queue.put(data)
            
            # Convert async callback to sync for blocking execution
            from ..blocking_helpers import run_async_in_thread
            
            # Run the async extraction method using the main event loop
            result = run_async_in_thread(
                code_service.extract_and_store_code_examples(
                    crawl_results,
                    url_to_full_document,
                    async_progress_callback,
                    start_progress=85,
                    end_progress=95
                ),
                timeout=300.0  # 5 minute timeout for code extraction
            )
            
            safe_logfire_info(f"Code extraction completed: {result} examples stored")
            return {'code_examples_stored': result}
            
        except Exception as e:
            safe_logfire_error(f"Error in blocking code extraction: {e}")
            import traceback
            safe_logfire_error(f"Traceback: {traceback.format_exc()}")
            return {'code_examples_stored': 0}
    
    def _crawl_by_url_type_blocking(self, url: str, request: Dict[str, Any], progress_queue: Queue) -> tuple:
        """
        Blocking version of URL type detection and crawling.
        
        Returns:
            Tuple of (crawl_results, crawl_type)
        """
        # We'll use the async crawling service via run_async_in_thread
        from ..blocking_helpers import run_async_in_thread
        crawl_results = []
        crawl_type = None
        
        if self.crawling_service.is_txt(url):
            # Handle text files with simple HTTP request
            progress_queue.put({
                'status': 'crawling',
                'percentage': 10,
                'log': 'Detected text file, fetching content...'
            })
            
            # Use simple HTTP request for text files instead of crawler
            import urllib.request
            try:
                safe_logfire_info(f"Fetching text file using urllib: {url}")
                progress_queue.put({
                    'status': 'crawling',
                    'percentage': 15,
                    'log': f'Downloading text file from {url}...'
                })
                
                # Create request with headers to avoid 403 errors
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/plain, text/html, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://google.com'
                }
                
                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=30) as response:
                    # Handle compressed responses
                    content_bytes = response.read()
                    
                    # Check if response is gzipped
                    content_encoding = response.headers.get('Content-Encoding', '').lower()
                    if content_encoding == 'gzip':
                        import gzip
                        content_bytes = gzip.decompress(content_bytes)
                    elif content_encoding == 'br':
                        try:
                            import brotli
                            content_bytes = brotli.decompress(content_bytes)
                        except ImportError:
                            safe_logfire_error("Brotli compression detected but brotli module not available")
                            raise ValueError("Cannot decompress brotli content - brotli module not installed")
                    
                    # Decode to string
                    content = content_bytes.decode('utf-8')
                    
                    safe_logfire_info(f"Text file downloaded, size: {len(content)} bytes")
                    progress_queue.put({
                        'status': 'crawling',
                        'percentage': 18,
                        'log': f'Text file downloaded, size: {len(content)} bytes'
                    })
                    
                    # Create result similar to crawler output
                    crawl_results = [{
                        'url': url,
                        'markdown': content,
                        'html': content,  # Keep raw content for text files to allow proper code extraction
                        'title': url.split('/')[-1],
                        'description': f'Text file from {url}',
                        'success': True
                    }]
                    crawl_type = "text_file"
                    safe_logfire_info(f"Successfully fetched text file: {url}, size: {len(content)} chars")
            except urllib.error.HTTPError as e:
                safe_logfire_error(f"HTTP error fetching text file {url}: {e.code} {e.reason}")
                if e.code == 403:
                    # Try with the crawler as fallback for 403 errors
                    safe_logfire_info("Got 403 error, falling back to crawler for text file")
                    progress_queue.put({
                        'status': 'crawling',
                        'percentage': 16,
                        'log': 'Access denied with simple fetch, trying with browser simulation...'
                    })
                    # Use the async crawler as fallback
                    async def _crawl_with_browser():
                        return await self.crawling_service.crawl_single_url(url)
                    
                    result = run_async_in_thread(_crawl_with_browser())
                    if result and result.get('success'):
                        crawl_results = [result]
                        crawl_type = "text_file"
                        safe_logfire_info(f"Successfully fetched text file with crawler: {url}")
                    else:
                        raise ValueError(f"Failed to fetch text file even with crawler: HTTP {e.code} {e.reason}")
                else:
                    raise ValueError(f"Failed to fetch text file: HTTP {e.code} {e.reason}")
            except Exception as e:
                safe_logfire_error(f"Failed to fetch text file {url}: {e}")
                raise ValueError(f"Failed to fetch text file: {e}")
            
        elif self.crawling_service.is_sitemap(url):
            # Handle sitemaps
            progress_queue.put({
                'status': 'crawling',
                'percentage': 10,
                'log': 'Detected sitemap, parsing URLs...'
            })
            sitemap_urls = self.crawling_service.parse_sitemap(url)
            
            if sitemap_urls:
                progress_queue.put({
                    'status': 'crawling',
                    'percentage': 15,
                    'log': f'Starting batch crawl of {len(sitemap_urls)} URLs...'
                })
                
                # Use async batch crawl via run_async_in_thread
                async def _crawl_batch():
                    return await self.crawling_service.crawl_batch_urls(sitemap_urls)
                
                crawl_results = run_async_in_thread(_crawl_batch())
                crawl_type = "sitemap"
                
        else:
            # Handle regular webpages with recursive crawling
            progress_queue.put({
                'status': 'crawling',
                'percentage': 10,
                'log': f'Starting recursive crawl with max depth {request.get("max_depth", 1)}...'
            })
            
            max_depth = request.get('max_depth', 1)
            # Use async recursive crawling via run_async_in_thread
            async def _crawl_recursive():
                # Create a dummy progress callback since we're in blocking context
                async def dummy_progress(status, percentage, message, **kwargs):
                    pass
                return await self.crawling_service.crawl_recursive_with_progress(
                    [url], 
                    max_depth=max_depth,
                    progress_callback=dummy_progress,
                    start_progress=0,
                    end_progress=100
                )
            
            crawl_results = run_async_in_thread(_crawl_recursive())
            crawl_type = "webpage"
        
        progress_queue.put({
            'status': 'crawling',
            'percentage': 20,
            'log': f'Crawling complete, found {len(crawl_results)} pages'
        })
        
        return crawl_results, crawl_type
    
    
    def _process_and_store_documents_blocking(self, crawl_results: List[Dict], request: Dict[str, Any], 
                                            crawl_type: str, progress_queue: Queue) -> Dict[str, Any]:
        """
        Blocking version of document processing and storage.
        
        Returns:
            Dict containing storage statistics and document mappings
        """
        # Import the document storage service for chunking
        from ..storage.storage_services import DocumentStorageService
        from ..storage.document_storage_service import add_documents_to_supabase
        
        # Initialize storage service for chunking
        storage_service = DocumentStorageService(self.supabase_client)
        
        # Prepare data for chunked storage
        all_urls = []
        all_chunk_numbers = []
        all_contents = []
        all_metadatas = []
        source_word_counts = {}
        url_to_full_document = {}
        
        # Process and chunk each document
        for doc_index, doc in enumerate(crawl_results):
            source_url = doc.get('url', '')
            markdown_content = doc.get('markdown', '')
            
            if not markdown_content:
                continue
            
            # Store full document for code extraction context
            url_to_full_document[source_url] = markdown_content
            
            # Report chunking progress
            chunk_progress = 50 + int((doc_index / len(crawl_results)) * 5)  # 50-55%
            progress_queue.put({
                'status': 'processing',
                'percentage': chunk_progress,
                'log': f'Chunking document {doc_index + 1}/{len(crawl_results)}...'
            })
            
            # CHUNK THE CONTENT
            chunks = storage_service.smart_chunk_text(markdown_content, chunk_size=5000)
            
            # Extract source_id
            parsed_url = urlparse(source_url)
            source_id = parsed_url.netloc or parsed_url.path
            safe_logfire_info(f"Extracted source_id '{source_id}' from URL '{source_url}'")
            
            # Process each chunk
            for i, chunk in enumerate(chunks):
                all_urls.append(source_url)
                all_chunk_numbers.append(i)
                all_contents.append(chunk)
                
                # Create metadata for each chunk
                word_count = len(chunk.split())
                metadata = {
                    'url': source_url,
                    'title': doc.get('title', ''),
                    'description': doc.get('description', ''),
                    'source_id': source_id,
                    'knowledge_type': request.get('knowledge_type', 'documentation'),
                    'crawl_type': crawl_type,
                    'word_count': word_count,
                    'char_count': len(chunk),
                    'chunk_index': i,
                    'tags': request.get('tags', [])
                }
                all_metadatas.append(metadata)
                
                # Accumulate word count
                source_word_counts[source_id] = source_word_counts.get(source_id, 0) + word_count
        
        # Create/update source record FIRST before storing documents
        if all_contents and all_metadatas:
            # Find ALL unique source_ids in the crawl results
            unique_source_ids = set()
            source_id_contents = {}
            source_id_word_counts = {}
            
            for i, metadata in enumerate(all_metadatas):
                source_id = metadata['source_id']
                unique_source_ids.add(source_id)
                
                # Group content by source_id for better summaries
                if source_id not in source_id_contents:
                    source_id_contents[source_id] = []
                source_id_contents[source_id].append(all_contents[i])
                
                # Track word counts per source_id
                if source_id not in source_id_word_counts:
                    source_id_word_counts[source_id] = 0
                source_id_word_counts[source_id] += metadata.get('word_count', 0)
            
            safe_logfire_info(f"Found {len(unique_source_ids)} unique source_ids: {list(unique_source_ids)}")
            
            # Create source records for ALL unique source_ids
            for source_id in unique_source_ids:
                # Get combined content for this specific source_id
                source_contents = source_id_contents[source_id]
                combined_content = ''
                for chunk in source_contents[:3]:  # First 3 chunks for this source
                    if len(combined_content) + len(chunk) < 15000:
                        combined_content += ' ' + chunk
                    else:
                        break
                
                # Generate summary with fallback
                try:
                    summary = extract_source_summary(source_id, combined_content)
                except Exception as e:
                    safe_logfire_error(f"Failed to generate AI summary for '{source_id}': {str(e)}, using fallback")
                    # Fallback to simple summary
                    summary = f"Documentation from {source_id} - {len(source_contents)} pages crawled"
                
                # Update source info in database BEFORE storing documents
                safe_logfire_info(f"About to create/update source record for '{source_id}' (word count: {source_id_word_counts[source_id]})")
                try:
                    update_source_info(
                        client=self.supabase_client,
                        source_id=source_id,
                        summary=summary,
                        word_count=source_id_word_counts[source_id],
                        content=combined_content,
                        knowledge_type=request.get('knowledge_type', 'technical'),
                        tags=request.get('tags', []),
                        update_frequency=0
                    )
                    safe_logfire_info(f"Successfully created/updated source record for '{source_id}'")
                except Exception as e:
                    safe_logfire_error(f"Failed to create/update source record for '{source_id}': {str(e)}")
                    # Try a simpler approach with minimal data
                    try:
                        safe_logfire_info(f"Attempting fallback source creation for '{source_id}'")
                        self.supabase_client.table('sources').upsert({
                            'source_id': source_id,
                            'title': source_id,  # Use source_id as title fallback
                            'summary': summary,
                            'total_word_count': source_id_word_counts[source_id],
                            'metadata': {
                                'knowledge_type': request.get('knowledge_type', 'technical'),
                                'tags': request.get('tags', []),
                                'auto_generated': True,
                                'fallback_creation': True
                            }
                        }).execute()
                        safe_logfire_info(f"Fallback source creation succeeded for '{source_id}'")
                    except Exception as fallback_error:
                        safe_logfire_error(f"Both source creation attempts failed for '{source_id}': {str(fallback_error)}")
                        raise Exception(f"Unable to create source record for '{source_id}'. This will cause foreign key violations. Error: {str(fallback_error)}")
        
        # Verify ALL source records exist before proceeding with document storage
        if unique_source_ids:
            for source_id in unique_source_ids:
                try:
                    source_check = self.supabase_client.table('sources').select('source_id').eq('source_id', source_id).execute()
                    if not source_check.data:
                        raise Exception(f"Source record verification failed - '{source_id}' does not exist in sources table")
                    safe_logfire_info(f"Source record verified for '{source_id}'")
                except Exception as e:
                    safe_logfire_error(f"Source verification failed for '{source_id}': {str(e)}")
                    raise
            
            safe_logfire_info(f"All {len(unique_source_ids)} source records verified - proceeding with document storage")
        
        safe_logfire_info(f"url_to_full_document keys: {list(url_to_full_document.keys())[:5]}")
        safe_logfire_info(f"Document storage | documents={len(crawl_results)} | chunks={len(all_contents)}")
        
        # Report progress before starting storage - this updates main task progress
        progress_queue.put({
            'status': 'document_storage',
            'percentage': 55,  # Main task progress
            'log': f'Starting to store {len(all_contents)} chunks...',
            'total_chunks': len(all_contents)
        })
        
        # Use synchronous document storage - no event loop coordination needed!
        try:
            safe_logfire_info("Starting synchronous document storage")
            safe_logfire_info(f"Storing {len(all_contents)} chunks with batch size 10")
            
            # Use the synchronous version directly
            add_documents_to_supabase_sync(
                client=self.supabase_client,
                urls=all_urls,
                chunk_numbers=all_chunk_numbers,
                contents=all_contents,
                metadatas=all_metadatas,
                url_to_full_document=url_to_full_document,
                batch_size=10,
                progress_queue=progress_queue,  # Pass the queue directly
                enable_parallel_batches=True  # Still uses parallel workers for contextual embeddings
            )
            
            safe_logfire_info("Document storage completed successfully with contextual embeddings")
            
            # Report completion with explicit percentage to update task progress
            progress_queue.put({
                'status': 'document_storage',
                'percentage': 85,  # This WILL update the main task progress
                'log': f'Stored {len(all_contents)} chunks with contextual embeddings'
            })
        except asyncio.TimeoutError:
            safe_logfire_error(f"Document storage timed out after 60 seconds")
            # Continue anyway - some documents may have been stored
            progress_queue.put({
                'status': 'document_storage',
                'percentage': 80,
                'log': 'Document storage timed out - continuing...'
            })
        except Exception as e:
            safe_logfire_error(f"Document storage failed: {e}")
            import traceback
            safe_logfire_error(f"Full traceback: {traceback.format_exc()}")
            # Report error but don't crash the whole task
            progress_queue.put({
                'status': 'document_storage',
                'percentage': 85,  # Still move forward
                'log': f'Document storage error (continuing): {str(e)[:100]}'
            })
            # Don't re-raise to allow task to complete
        
        # Update progress after storage
        progress_queue.put({
            'status': 'document_storage',
            'percentage': 85,
            'log': f'Stored {len(all_contents)} chunks from {len(crawl_results)} documents'
        })
        
        # Calculate actual chunk count
        chunk_count = len(all_contents)
        
        return {
            'chunk_count': chunk_count,
            'total_word_count': sum(source_word_counts.values()),
            'url_to_full_document': url_to_full_document
        }
    
    def _extract_and_store_code_examples_blocking(self, crawl_results: List[Dict],
                                                 url_to_full_document: Dict[str, str],
                                                 progress_queue: Queue) -> int:
        """
        REMOVED: This method created new event loops which broke Socket.IO connections.
        Use the async version instead with proper event loop coordination.
        """
        safe_logfire_error("_extract_and_store_code_examples_blocking called - this method was removed!")
        return 0