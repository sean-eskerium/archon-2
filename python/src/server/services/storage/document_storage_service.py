"""
Document Storage Service

Handles storage of documents in Supabase with parallel processing support.
"""
import os
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional
from supabase import Client
from urllib.parse import urlparse

from ...config.logfire_config import search_logger, safe_span
from ..embeddings.embedding_service import create_embeddings_batch_async
from ..embeddings.contextual_embedding_service import (
    process_chunk_with_context,
    generate_contextual_embeddings_batch
)
from ..client_manager import get_supabase_client
from ..credential_service import credential_service


async def add_documents_to_supabase(
    client, 
    urls: List[str], 
    chunk_numbers: List[int],
    contents: List[str], 
    metadatas: List[Dict[str, Any]],
    url_to_full_document: Dict[str, str],
    batch_size: int = 15,
    progress_callback: Optional[Any] = None,
    enable_parallel_batches: bool = True,
    provider: Optional[str] = None
) -> None:
    """
    Add documents to Supabase with threading optimizations.
    
    This is the simpler sequential version for smaller batches.
    
    Args:
        client: Supabase client
        urls: List of URLs
        chunk_numbers: List of chunk numbers
        contents: List of document contents
        metadatas: List of document metadata
        url_to_full_document: Dictionary mapping URLs to their full document content
        batch_size: Size of each batch for insertion
        progress_callback: Optional async callback function for progress reporting
        provider: Optional provider override for embeddings
    """
    with safe_span("add_documents_to_supabase",
                           total_documents=len(contents),
                           batch_size=batch_size) as span:
        
        # Simple progress reporting helper with batch info support
        async def report_progress(message: str, percentage: int, batch_info: dict = None):
            if progress_callback and asyncio.iscoroutinefunction(progress_callback):
                await progress_callback(message, percentage, batch_info)
        
        # Get unique URLs to delete existing records
        unique_urls = list(set(urls))
        
        # Delete existing records for these URLs
        try:
            if unique_urls:
                client.table("crawled_pages").delete().in_("url", unique_urls).execute()
                search_logger.info(f"Deleted existing records for {len(unique_urls)} URLs")
        except Exception as e:
            search_logger.warning(f"Batch delete failed: {e}. Trying one-by-one deletion as fallback.")
            # Fallback: delete records one by one
            for url in unique_urls:
                try:
                    client.table("crawled_pages").delete().eq("url", url).execute()
                except Exception as inner_e:
                    search_logger.error(f"Error deleting record for URL {url}: {inner_e}")
        
        # Check if contextual embeddings are enabled
        # Fix: Get from credential service instead of environment
        from ..credential_service import credential_service
        try:
            use_contextual_embeddings = await credential_service.get_credential("USE_CONTEXTUAL_EMBEDDINGS", "false", decrypt=True)
            if isinstance(use_contextual_embeddings, str):
                use_contextual_embeddings = use_contextual_embeddings.lower() == "true"
        except:
            # Fallback to environment variable
            use_contextual_embeddings = os.getenv("USE_CONTEXTUAL_EMBEDDINGS", "false") == "true"
        
        # Initialize batch tracking for simplified progress
        completed_batches = 0
        total_batches = (len(contents) + batch_size - 1) // batch_size
        
        # Process in batches to avoid memory issues
        for batch_num, i in enumerate(range(0, len(contents), batch_size), 1):
            batch_end = min(i + batch_size, len(contents))
            
            # Get batch slices
            batch_urls = urls[i:batch_end]
            batch_chunk_numbers = chunk_numbers[i:batch_end]
            batch_contents = contents[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            
            # Simple batch progress - only track completed batches
            current_percentage = int((completed_batches / total_batches) * 100)
            
            # Get max workers setting FIRST before using it
            if use_contextual_embeddings:
                try:
                    max_workers = await credential_service.get_credential("CONTEXTUAL_EMBEDDINGS_MAX_WORKERS", "4", decrypt=True)
                    max_workers = int(max_workers)
                except:
                    max_workers = 4
            else:
                max_workers = 1
            
            # Report batch start with simplified progress
            if progress_callback and asyncio.iscoroutinefunction(progress_callback):
                await progress_callback(
                    f"Processing batch {batch_num}/{total_batches} ({len(batch_contents)} chunks)",
                    current_percentage,
                    {
                        'current_batch': batch_num,
                        'total_batches': total_batches,
                        'completed_batches': completed_batches,
                        'chunks_in_batch': len(batch_contents),
                        'max_workers': max_workers if use_contextual_embeddings else 0
                    }
                )
            
            # Skip batch start progress to reduce Socket.IO traffic
            # Only report on completion
            
            # Apply contextual embedding to each chunk if enabled
            if use_contextual_embeddings:
                
                # Prepare arguments for parallel processing
                process_args = []
                for j, content in enumerate(batch_contents):
                    url = batch_urls[j]
                    full_document = url_to_full_document.get(url, "")
                    process_args.append((url, content, full_document))
                
                # Track processing
                contextual_contents = [None] * len(batch_contents)
                
                # Process in parallel using ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all tasks and collect futures with their indices
                    future_to_idx = {executor.submit(process_chunk_with_context, arg): idx 
                                   for idx, arg in enumerate(process_args)}
                    
                    # Process results as they complete
                    for future in concurrent.futures.as_completed(future_to_idx):
                        idx = future_to_idx[future]
                        try:
                            result, success = future.result()
                            contextual_contents[idx] = result
                            if success:
                                batch_metadatas[idx]["contextual_embedding"] = True
                                search_logger.debug(f"Successfully generated contextual embedding for chunk {idx} in batch {batch_num}")
                        except Exception as e:
                            search_logger.warning(f"Error processing chunk {idx}: {e}")
                            # Use original content as fallback
                            contextual_contents[idx] = batch_contents[idx]
                
                # Ensure all results are populated (shouldn't be None if everything worked)
                for idx, content in enumerate(contextual_contents):
                    if content is None:
                        contextual_contents[idx] = batch_contents[idx]
                
                # Log summary of contextual embedding results
                successful_count = sum(1 for meta in batch_metadatas if meta.get("contextual_embedding", False))
                search_logger.info(f"Batch {batch_num}: Generated {successful_count}/{len(batch_contents)} contextual embeddings using {max_workers} workers")
            else:
                # If not using contextual embeddings, use original contents
                contextual_contents = batch_contents
            
            # Create embeddings for the batch - no progress reporting
            # Don't pass websocket to avoid Socket.IO issues
            batch_embeddings = await create_embeddings_batch_async(
                contextual_contents,
                provider=provider
            )
            
            # Prepare batch data
            batch_data = []
            for j in range(len(contextual_contents)):
                # Use source_id from metadata if available, otherwise extract from URL
                if batch_metadatas[j].get('source_id'):
                    source_id = batch_metadatas[j]['source_id']
                else:
                    # Fallback: Extract source_id from URL
                    parsed_url = urlparse(batch_urls[j])
                    source_id = parsed_url.netloc or parsed_url.path
                
                data = {
                    "url": batch_urls[j],
                    "chunk_number": batch_chunk_numbers[j],
                    "content": contextual_contents[j],
                    "metadata": {
                        "chunk_size": len(contextual_contents[j]),
                        **batch_metadatas[j]
                    },
                    "source_id": source_id,
                    "embedding": batch_embeddings[j]
                }
                batch_data.append(data)
            
            # Insert batch with retry logic - no progress reporting
            
            max_retries = 3
            retry_delay = 1.0
            
            for retry in range(max_retries):
                try:
                    client.table("crawled_pages").insert(batch_data).execute()
                    
                    # Increment completed batches and report simple progress
                    completed_batches += 1
                    # Ensure last batch reaches 100%
                    if completed_batches == total_batches:
                        new_percentage = 100
                    else:
                        new_percentage = int((completed_batches / total_batches) * 100)
                    
                    complete_msg = f"Completed batch {batch_num}/{total_batches} ({len(batch_data)} chunks)"
                    
                    # Simple batch completion info
                    batch_info = {
                        'completed_batches': completed_batches,
                        'total_batches': total_batches,
                        'current_batch': batch_num,
                        'chunks_processed': len(batch_data),
                        'max_workers': max_workers if use_contextual_embeddings else 0
                    }
                    await report_progress(complete_msg, new_percentage, batch_info)
                    break
                    
                except Exception as e:
                    if retry < max_retries - 1:
                        search_logger.warning(f"Error inserting batch (attempt {retry + 1}/{max_retries}): {e}")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        search_logger.error(f"Failed to insert batch after {max_retries} attempts: {e}")
                        # Try individual inserts as last resort
                        successful_inserts = 0
                        for record in batch_data:
                            try:
                                client.table("crawled_pages").insert(record).execute()
                                successful_inserts += 1
                            except Exception as individual_error:
                                search_logger.error(f"Failed individual insert for {record['url']}: {individual_error}")
                        
                        search_logger.info(f"Individual inserts: {successful_inserts}/{len(batch_data)} successful")
            
            # WebSocket-safe delay between batches
            if i + batch_size < len(contents):
                delay = 1.5 if use_contextual_embeddings else 0.5
                await asyncio.sleep(delay)
        
        # Send final 100% progress report to ensure UI shows completion
        if progress_callback and asyncio.iscoroutinefunction(progress_callback):
            await progress_callback(
                f"Document storage completed: {len(contents)} chunks stored in {total_batches} batches",
                100,  # Ensure we report 100%
                {
                    'completed_batches': total_batches,
                    'total_batches': total_batches,
                    'current_batch': total_batches,
                    'chunks_processed': len(contents)
                    # DON'T send 'status': 'completed' - that's for the orchestration service only!
                }
            )
        
        span.set_attribute("success", True)
        span.set_attribute("total_processed", len(contents))


