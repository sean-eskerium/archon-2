"""
Utility functions for the Crawl4AI MCP server.
"""
import os
import concurrent.futures
from typing import List, Dict, Any, Optional, Tuple
import json
from supabase import create_client, Client
from urllib.parse import urlparse
import openai
import re
import time
import asyncio
import logging
import uuid
from datetime import datetime
import threading

# Import Logfire
from .logfire_config import search_logger

# OpenAI client will be configured dynamically when needed

# Deprecated functions - kept for backwards compatibility but should not be used
# The OpenAI API key is loaded into environment at startup via initialize_credentials()
# All code should use os.getenv("OPENAI_API_KEY") directly

async def get_openai_api_key() -> Optional[str]:
    """
    DEPRECATED: Use os.getenv("OPENAI_API_KEY") directly.
    API key is loaded into environment at startup.
    """
    return os.getenv("OPENAI_API_KEY")

def get_openai_api_key_sync() -> Optional[str]:
    """
    DEPRECATED: Use os.getenv("OPENAI_API_KEY") directly.
    API key is loaded into environment at startup.
    """
    return os.getenv("OPENAI_API_KEY")

def get_supabase_client() -> Client:
    """
    Get a Supabase client with the URL and key from environment variables.
    Uses the standard Supabase client initialization.
    
    Returns:
        Supabase client instance
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
    
    try:
        # Initialize with standard Supabase client - no need for custom headers
        client = create_client(url, key)
        
        # Extract project ID from URL for logging purposes only
        import re
        match = re.match(r'https://([^.]+)\.supabase\.co', url)
        if match:
            project_id = match.group(1)
            print(f"Supabase client initialized for project: {project_id}")
        else:
            print("Supabase client initialized successfully")
        
        return client
    except Exception as e:
        logging.error(f"Error initializing Supabase client: {e}")
        raise

def create_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Create embeddings for multiple texts in a single API call.
    
    Args:
        texts: List of texts to create embeddings for
        
    Returns:
        List of embeddings (each embedding is a list of floats)
    """
    if not texts:
        return []
    
    # Get API key directly from environment (loaded at startup)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: No OpenAI API key found in environment")
        return [[0.0] * 1536 for _ in texts]
    
    # Create OpenAI client with the API key
    client = openai.OpenAI(api_key=api_key)
    
    max_retries = 3
    retry_delay = 1.0  # Start with 1 second delay
    
    for retry in range(max_retries):
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small", # Hardcoding embedding model for now, will change this later to be more dynamic
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            if retry < max_retries - 1:
                print(f"Error creating batch embeddings (attempt {retry + 1}/{max_retries}): {e}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to create batch embeddings after {max_retries} attempts: {e}")
                # Try creating embeddings one by one as fallback
                print("Attempting to create embeddings individually...")
                embeddings = []
                successful_count = 0
                
                for i, text in enumerate(texts):
                    try:
                        individual_response = client.embeddings.create(
                            model="text-embedding-3-small",
                            input=[text]
                        )
                        embeddings.append(individual_response.data[0].embedding)
                        successful_count += 1
                    except Exception as individual_error:
                        print(f"Failed to create embedding for text {i}: {individual_error}")
                        # Add zero embedding as fallback
                        embeddings.append([0.0] * 1536)
                
                print(f"Successfully created {successful_count}/{len(texts)} embeddings individually")
                return embeddings

def create_embedding(text: str) -> List[float]:
    """
    Create an embedding for a single text using OpenAI's API.
    
    Args:
        text: Text to create an embedding for
        
    Returns:
        List of floats representing the embedding
    """
    try:
        embeddings = create_embeddings_batch([text])
        return embeddings[0] if embeddings else [0.0] * 1536
    except Exception as e:
        print(f"Error creating embedding: {e}")
        # Return empty embedding if there's an error
        return [0.0] * 1536

def generate_contextual_embedding(full_document: str, chunk: str) -> Tuple[str, bool]:
    """
    Generate contextual information for a chunk within a document to improve retrieval.
    
    Args:
        full_document: The complete document text
        chunk: The specific chunk of text to generate context for
        
    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    # Get API key directly from environment (loaded at startup)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: No OpenAI API key found in environment")
        return chunk, False
    
    # Create OpenAI client with the API key
    client = openai.OpenAI(api_key=api_key)
    
    model_choice = os.getenv("MODEL_CHOICE")
    
    try:
        # Create the prompt for generating contextual information
        # Reduced from 25000 to 5000 to avoid token rate limits
        prompt = f"""<document> 
{full_document[:5000]} 
</document>
Here is the chunk we want to situate within the whole document 
<chunk> 
{chunk}
</chunk> 
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

        # Call the OpenAI API to generate contextual information
        response = client.chat.completions.create(
            model=model_choice,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise contextual information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        # Extract the generated context
        context = response.choices[0].message.content.strip()
        
        # Combine the context with the original chunk
        contextual_text = f"{context}\n---\n{chunk}"
        
        # Add a small delay to prevent rate limiting when running in parallel
        time.sleep(0.3)  # Keep as time.sleep - this is in a sync function
        
        return contextual_text, True
    
    except Exception as e:
        error_str = str(e)
        if "rate_limit_exceeded" in error_str:
            print(f"RATE LIMIT HIT in contextual embedding: {error_str[:200]}...")
        else:
            print(f"Error generating contextual embedding: {e}. Using original chunk instead.")
        return chunk, False

def process_chunk_with_context(args):
    """
    Process a single chunk with contextual embedding.
    This function is designed to be used with concurrent.futures.
    
    Args:
        args: Tuple containing (url, content, full_document)
        
    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    url, content, full_document = args
    return generate_contextual_embedding(full_document, content)

async def add_documents_to_supabase(
    client: Client, 
    urls: List[str], 
    chunk_numbers: List[int],
    contents: List[str], 
    metadatas: List[Dict[str, Any]],
    url_to_full_document: Dict[str, str],
    batch_size: int = 15,
    progress_callback: Optional[Any] = None
) -> None:
    """
    Add documents to the Supabase crawled_pages table in batches.
    Deletes existing records with the same URLs before inserting to prevent duplicates.
    
    Args:
        client: Supabase client
        urls: List of URLs
        chunk_numbers: List of chunk numbers
        contents: List of document contents
        metadatas: List of document metadata
        url_to_full_document: Dictionary mapping URLs to their full document content
        batch_size: Size of each batch for insertion
        progress_callback: Optional async callback function for progress reporting
    """
    # Get unique URLs to delete existing records
    unique_urls = list(set(urls))
    
    # Delete existing records for these URLs in a single operation
    try:
        if unique_urls:
            # Use the .in_() filter to delete all records with matching URLs
            client.table("crawled_pages").delete().in_("url", unique_urls).execute()
    except Exception as e:
        print(f"Batch delete failed: {e}. Trying one-by-one deletion as fallback.")
        # Fallback: delete records one by one
        for url in unique_urls:
            try:
                client.table("crawled_pages").delete().eq("url", url).execute()
            except Exception as inner_e:
                print(f"Error deleting record for URL {url}: {inner_e}")
                # Continue with the next URL even if one fails
    
    # Check if MODEL_CHOICE is set for contextual embeddings
    use_contextual_embeddings = os.getenv("USE_CONTEXTUAL_EMBEDDINGS", "false") == "true"
    # Increased back to 2 workers - should be safe with 5k context
    max_workers = int(os.getenv("CONTEXTUAL_EMBEDDINGS_MAX_WORKERS", "2"))
    print(f"\n\nUse contextual embeddings: {use_contextual_embeddings}")
    print(f"Max workers for contextual embeddings: {max_workers}")
    print(f"Total documents to process: {len(contents)}")
    print(f"Batch size: {batch_size}\n\n")
    
    # Process in batches to avoid memory issues
    total_batches = (len(contents) + batch_size - 1) // batch_size
    
    # Helper function to report progress
    async def report_progress(message: str, percentage: int):
        if progress_callback and asyncio.iscoroutinefunction(progress_callback):
            await progress_callback('document_storage', percentage, message)
        # Always print for debugging
        print(f"Progress: {message} ({percentage}%)")
    
    for batch_num, i in enumerate(range(0, len(contents), batch_size), 1):
        batch_end = min(i + batch_size, len(contents))
        batch_progress_msg = f"Batch {batch_num}/{total_batches}: Processing items {i+1}-{batch_end} of {len(contents)}"
        print(f"\n{batch_progress_msg}")
        
        # Calculate overall progress based on documents processed so far
        # This gives smooth progress from 0-100% across all batches
        # For first batch, start at 10% to avoid any reset issues
        if i == 0:
            overall_percentage = 10  # Start at 10% for first batch
        else:
            documents_processed_so_far = i
            overall_percentage = int((documents_processed_so_far / len(contents)) * 100)
        
        await report_progress(batch_progress_msg, overall_percentage)
        
        # Get batch slices
        batch_urls = urls[i:batch_end]
        batch_chunk_numbers = chunk_numbers[i:batch_end]
        batch_contents = contents[i:batch_end]
        batch_metadatas = metadatas[i:batch_end]
        
        # Apply contextual embedding to each chunk if MODEL_CHOICE is set
        if use_contextual_embeddings:
            # Report that we're creating contextual embeddings
            # Add small increment to show progress within batch
            embedding_msg = f"Batch {batch_num}/{total_batches}: Creating contextual embeddings..."
            embedding_percentage = overall_percentage + int((5 / 100) * (100 / total_batches))
            await report_progress(embedding_msg, min(embedding_percentage, 99))
            
            # Prepare arguments for parallel processing
            process_args = []
            for j, content in enumerate(batch_contents):
                url = batch_urls[j]
                full_document = url_to_full_document.get(url, "")
                process_args.append((url, content, full_document))
            
            # Estimate token usage for this batch
            avg_chunk_size = sum(len(c) for c in batch_contents) // len(batch_contents)
            estimated_tokens = (5000 + avg_chunk_size) * len(batch_contents) // 4  # Rough estimate: 1 token = 4 chars
            print(f"Estimated tokens for this batch: ~{estimated_tokens:,} tokens")
            
            # Process in parallel using asyncio's run_in_executor to prevent blocking
            contextual_contents = [None] * len(batch_contents)  # Pre-allocate with None
            loop = asyncio.get_event_loop()
            
            # Create tasks for all chunks
            tasks = []
            for idx, arg in enumerate(process_args):
                # Run the synchronous function in a thread pool to prevent blocking
                task = loop.run_in_executor(None, process_chunk_with_context, arg)
                tasks.append((idx, task))
            
            # Wait for all tasks to complete
            for idx, task in tasks:
                try:
                    result, success = await task
                    contextual_contents[idx] = result  # Store in correct position!
                    if success:
                        batch_metadatas[idx]["contextual_embedding"] = True
                except Exception as e:
                    print(f"Error processing chunk {idx}: {e}")
                    # Use original content as fallback
                    contextual_contents[idx] = batch_contents[idx]
            
            # Check for any None values and replace with original content
            for idx, content in enumerate(contextual_contents):
                if content is None:
                    print(f"Warning: Missing result for chunk {idx}, using original content")
                    contextual_contents[idx] = batch_contents[idx]
        else:
            # If not using contextual embeddings, use original contents
            contextual_contents = batch_contents
        
        # Create embeddings for the entire batch at once
        embeddings_msg = f"Batch {batch_num}/{total_batches}: Creating embeddings..."
        embeddings_percentage = overall_percentage + int((10 / 100) * (100 / total_batches))
        await report_progress(embeddings_msg, min(embeddings_percentage, 99))
        # TODO: Pass cached API key to this function when called from context
        batch_embeddings = create_embeddings_batch(contextual_contents)
        
        batch_data = []
        for j in range(len(contextual_contents)):
            # Extract metadata fields
            chunk_size = len(contextual_contents[j])
            
            # Extract source_id from URL
            parsed_url = urlparse(batch_urls[j])
            source_id = parsed_url.netloc or parsed_url.path
            
            # Prepare data for insertion
            data = {
                "url": batch_urls[j],
                "chunk_number": batch_chunk_numbers[j],
                "content": contextual_contents[j],  # Store original content
                "metadata": {
                    "chunk_size": chunk_size,
                    **batch_metadatas[j]
                },
                "source_id": source_id,  # Add source_id field
                "embedding": batch_embeddings[j]  # Use embedding from contextual content
            }
            
            batch_data.append(data)
        
        # Insert batch into Supabase with retry logic
        storing_msg = f"Batch {batch_num}/{total_batches}: Storing in database..."
        storing_percentage = overall_percentage + int((15 / 100) * (100 / total_batches))
        await report_progress(storing_msg, min(storing_percentage, 99))
        
        max_retries = 3
        retry_delay = 1.0  # Start with 1 second delay
        
        for retry in range(max_retries):
            try:
                client.table("crawled_pages").insert(batch_data).execute()
                # Success - report completion of this batch
                # Use consistent calculation based on documents processed
                completion_percentage = int(batch_end / len(contents) * 100)
                complete_msg = f"Batch {batch_num}/{total_batches}: Completed storing {len(batch_data)} chunks"
                await report_progress(complete_msg, completion_percentage)
                # Success - break out of retry loop
                break
            except Exception as e:
                if retry < max_retries - 1:
                    print(f"Error inserting batch into Supabase (attempt {retry + 1}/{max_retries}): {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)  # This function is async, so we can use await
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Final attempt failed
                    print(f"Failed to insert batch after {max_retries} attempts: {e}")
                    # Optionally, try inserting records one by one as a last resort
                    print("Attempting to insert records individually...")
                    successful_inserts = 0
                    for record in batch_data:
                        try:
                            client.table("crawled_pages").insert(record).execute()
                            successful_inserts += 1
                        except Exception as individual_error:
                            print(f"Failed to insert individual record for URL {record['url']}: {individual_error}")
                    
                    if successful_inserts > 0:
                        print(f"Successfully inserted {successful_inserts}/{len(batch_data)} records individually")
        
        # Add a delay between batches to prevent rate limiting
        if i + batch_size < len(contents):
            # Reduced delay - with 5k context we use much fewer tokens
            delay = 1.5 if use_contextual_embeddings else 0.5
            print(f"Waiting {delay} seconds before processing next batch...")
            await asyncio.sleep(delay)  # This function is async, so we can use await
    
    # Report final completion
    await report_progress(f"Successfully stored all {len(contents)} documents", 100)

def search_documents(
    client: Client,
    query: str,
    match_count: int = 5,
    threshold: float = 0.7,
    filter_metadata: dict = None,
    use_hybrid_search: bool = False,
    cached_api_key: str = None
) -> List[Dict[str, Any]]:
    """
    Search for documents in the database using semantic search.
    
    Args:
        client: Supabase client
        query: Search query string
        match_count: Number of results to return
        threshold: Similarity threshold for results
        filter_metadata: Optional metadata filter dict
        use_hybrid_search: Whether to use hybrid keyword + semantic search
        cached_api_key: Cached OpenAI API key for embeddings
    
    Returns:
        List of matching documents
    """
    with search_logger.span("vector_search", 
                           query_length=len(query),
                           match_count=match_count,
                           threshold=threshold,
                           has_filter=filter_metadata is not None) as span:
        try:
            search_logger.info("Document search started", 
                              query=query[:100] + "..." if len(query) > 100 else query,
                              match_count=match_count,
                              threshold=threshold,
                              filter_metadata=filter_metadata)
            
            # Create embedding for the query
            with search_logger.span("create_embedding"):
                query_embedding = create_embedding(query)
                
                if not query_embedding:
                    search_logger.error("Failed to create embedding for query")
                    return []
                
                span.set_attribute("embedding_dimensions", len(query_embedding))
            
            # Build the filter for the RPC call
            with search_logger.span("prepare_rpc_params"):
                rpc_params = {
                    "query_embedding": query_embedding,
                    "match_count": match_count
                }
                
                # Add filter to RPC params if provided
                if filter_metadata:
                    search_logger.debug("Adding filter to RPC params", filter_metadata=filter_metadata)
                    
                    # Check if we have a source filter specifically
                    if "source" in filter_metadata:
                        # Use the version with source_filter parameter
                        rpc_params["source_filter"] = filter_metadata["source"]
                        # Also add the general filter as empty jsonb to satisfy the function signature
                        rpc_params["filter"] = {}
                    else:
                        # Use the general filter parameter
                        rpc_params["filter"] = filter_metadata
                    
                    span.set_attribute("filter_applied", True)
                    span.set_attribute("filter_keys", list(filter_metadata.keys()) if filter_metadata else [])
                else:
                    # No filter provided - use empty jsonb for filter parameter
                    rpc_params["filter"] = {}
            
            # Call the RPC function
            with search_logger.span("supabase_rpc_call"):
                search_logger.debug("Calling Supabase RPC function", 
                                  function_name="match_crawled_pages",
                                  rpc_params_keys=list(rpc_params.keys()))
                
                response = client.rpc("match_crawled_pages", rpc_params).execute()
                span.set_attribute("rpc_success", True)
                span.set_attribute("raw_results_count", len(response.data) if response.data else 0)
            
            results_count = len(response.data) if response.data else 0
            
            span.set_attribute("success", True)
            span.set_attribute("final_results_count", results_count)
            
            if results_count > 0:
                search_logger.debug("Search results preview",
                                  first_result_url=response.data[0].get('url') if response.data else None,
                                  first_result_similarity=response.data[0].get('similarity') if response.data else None)
            
            search_logger.info("Document search completed successfully", 
                              final_results_count=results_count)
            
            return response.data or []
            
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("success", False)
            span.set_attribute("error_type", type(e).__name__)
            
            search_logger.exception("Document search failed",
                                   error=str(e),
                                   error_type=type(e).__name__,
                                   query=query[:50])
            # Return empty list on error instead of raising
            return []


def extract_code_blocks(markdown_content: str, min_length: int = 1000) -> List[Dict[str, Any]]:
    """
    Extract code blocks from markdown content along with context.
    
    Args:
        markdown_content: The markdown content to extract code blocks from
        min_length: Minimum length of code blocks to extract (default: 1000 characters)
        
    Returns:
        List of dictionaries containing code blocks and their context
    """
    code_blocks = []
    
    # Skip if content starts with triple backticks (edge case for files wrapped in backticks)
    content = markdown_content.strip()
    start_offset = 0
    if content.startswith('```'):
        # Skip the first triple backticks
        start_offset = 3
        print("Skipping initial triple backticks")
    
    # Find all occurrences of triple backticks
    backtick_positions = []
    pos = start_offset
    while True:
        pos = markdown_content.find('```', pos)
        if pos == -1:
            break
        backtick_positions.append(pos)
        pos += 3
    
    # Process pairs of backticks
    i = 0
    while i < len(backtick_positions) - 1:
        start_pos = backtick_positions[i]
        end_pos = backtick_positions[i + 1]
        
        # Extract the content between backticks
        code_section = markdown_content[start_pos+3:end_pos]
        
        # Check if there's a language specifier on the first line
        lines = code_section.split('\n', 1)
        if len(lines) > 1:
            # Check if first line is a language specifier (no spaces, common language names)
            first_line = lines[0].strip()
            if first_line and not ' ' in first_line and len(first_line) < 20:
                language = first_line
                code_content = lines[1].strip() if len(lines) > 1 else ""
            else:
                language = ""
                code_content = code_section.strip()
        else:
            language = ""
            code_content = code_section.strip()
        
        # Skip if code block is too short
        if len(code_content) < min_length:
            i += 2  # Move to next pair
            continue
        
        # Extract context before (1000 chars)
        context_start = max(0, start_pos - 1000)
        context_before = markdown_content[context_start:start_pos].strip()
        
        # Extract context after (1000 chars)
        context_end = min(len(markdown_content), end_pos + 3 + 1000)
        context_after = markdown_content[end_pos + 3:context_end].strip()
        
        code_blocks.append({
            'code': code_content,
            'language': language,
            'context_before': context_before,
            'context_after': context_after,
            'full_context': f"{context_before}\n\n{code_content}\n\n{context_after}"
        })
        
        # Move to next pair (skip the closing backtick we just processed)
        i += 2
    
    return code_blocks


def generate_code_example_summary(code: str, context_before: str, context_after: str) -> str:
    """
    Generate a summary for a code example using its surrounding context.
    
    Args:
        code: The code example
        context_before: Context before the code
        context_after: Context after the code
        
    Returns:
        A summary of what the code example demonstrates
    """
    # Get the decrypted API key
    api_key = get_openai_api_key_sync()
    if not api_key:
        print("Error: No OpenAI API key available for code example summary")
        return "Code example for demonstration purposes."
    
    # Create OpenAI client with the decrypted key
    client = openai.OpenAI(api_key=api_key)
    
    model_choice = os.getenv("MODEL_CHOICE")
    
    # Create the prompt
    prompt = f"""<context_before>
{context_before[-500:] if len(context_before) > 500 else context_before}
</context_before>

<code_example>
{code[:1500] if len(code) > 1500 else code}
</code_example>

<context_after>
{context_after[:500] if len(context_after) > 500 else context_after}
</context_after>

Based on the code example and its surrounding context, provide a concise summary (2-3 sentences) that describes what this code example demonstrates and its purpose. Focus on the practical application and key concepts illustrated.
"""
    
    try:
        response = client.chat.completions.create(
            model=model_choice,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise code example summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        result = response.choices[0].message.content.strip()
        
        # Add a small delay to prevent rate limiting when running in parallel
        time.sleep(0.3)  # Keep as time.sleep - this is in a sync function
        
        return result
    
    except Exception as e:
        print(f"Error generating code example summary: {e}")
        return "Code example for demonstration purposes."


def add_code_examples_to_supabase(
    client: Client,
    urls: List[str],
    chunk_numbers: List[int],
    code_examples: List[str],
    summaries: List[str],
    metadatas: List[Dict[str, Any]],
    batch_size: int = 20
):
    """
    Add code examples to the Supabase code_examples table in batches.
    
    Args:
        client: Supabase client
        urls: List of URLs
        chunk_numbers: List of chunk numbers
        code_examples: List of code example contents
        summaries: List of code example summaries
        metadatas: List of metadata dictionaries
        batch_size: Size of each batch for insertion
    """
    if not urls:
        return
        
    # Delete existing records for these URLs
    unique_urls = list(set(urls))
    for url in unique_urls:
        try:
            client.table('code_examples').delete().eq('url', url).execute()
        except Exception as e:
            print(f"Error deleting existing code examples for {url}: {e}")
    
    # Process in batches
    total_items = len(urls)
    for i in range(0, total_items, batch_size):
        batch_end = min(i + batch_size, total_items)
        batch_texts = []
        
        # Create combined texts for embedding (code + summary)
        for j in range(i, batch_end):
            combined_text = f"{code_examples[j]}\n\nSummary: {summaries[j]}"
            batch_texts.append(combined_text)
        
        # Create embeddings for the batch
        embeddings = create_embeddings_batch(batch_texts)
        
        # Check if embeddings are valid (not all zeros)
        valid_embeddings = []
        for embedding in embeddings:
            if embedding and not all(v == 0.0 for v in embedding):
                valid_embeddings.append(embedding)
            else:
                print(f"Warning: Zero or invalid embedding detected, creating new one...")
                # Try to create a single embedding as fallback
                single_embedding = create_embedding(batch_texts[len(valid_embeddings)])
                valid_embeddings.append(single_embedding)
        
        # Prepare batch data
        batch_data = []
        for j, embedding in enumerate(valid_embeddings):
            idx = i + j
            
            # Extract source_id from URL
            parsed_url = urlparse(urls[idx])
            source_id = parsed_url.netloc or parsed_url.path
            
            batch_data.append({
                'url': urls[idx],
                'chunk_number': chunk_numbers[idx],
                'content': code_examples[idx],
                'summary': summaries[idx],
                'metadata': metadatas[idx],  # Store as JSON object, not string
                'source_id': source_id,
                'embedding': embedding
            })
        
        # Insert batch into Supabase with retry logic
        max_retries = 3
        retry_delay = 1.0  # Start with 1 second delay
        
        for retry in range(max_retries):
            try:
                client.table('code_examples').insert(batch_data).execute()
                # Success - break out of retry loop
                break
            except Exception as e:
                if retry < max_retries - 1:
                    print(f"Error inserting batch into Supabase (attempt {retry + 1}/{max_retries}): {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)  # Keep as time.sleep - this is in a sync function
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Final attempt failed
                    print(f"Failed to insert batch after {max_retries} attempts: {e}")
                    # Optionally, try inserting records one by one as a last resort
                    print("Attempting to insert records individually...")
                    successful_inserts = 0
                    for record in batch_data:
                        try:
                            client.table('code_examples').insert(record).execute()
                            successful_inserts += 1
                        except Exception as individual_error:
                            print(f"Failed to insert individual record for URL {record['url']}: {individual_error}")
                    
                    if successful_inserts > 0:
                        print(f"Successfully inserted {successful_inserts}/{len(batch_data)} records individually")
        print(f"Inserted batch {i//batch_size + 1} of {(total_items + batch_size - 1)//batch_size} code examples")


def generate_source_title_and_metadata(source_id: str, content: str, knowledge_type: str = "technical", tags: List[str] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a descriptive title and metadata for a source using OpenAI.
    
    Args:
        source_id: The source ID (domain)
        content: The content to analyze
        knowledge_type: Type of knowledge (technical/business)
        tags: List of tags to include in metadata
        
    Returns:
        Tuple of (title, metadata_dict)
    """
    if tags is None:
        tags = []
    
    # Get the decrypted API key
    api_key = get_openai_api_key_sync()
    if not api_key:
        print(f"Error: No OpenAI API key available for title/metadata generation for {source_id}")
        return f"Content from {source_id}", {
            "knowledge_type": knowledge_type,
            "tags": tags,
            "auto_generated": False
        }
    
    # Create OpenAI client with the decrypted key
    client = openai.OpenAI(api_key=api_key)
    
    # Get the model choice from environment variables
    model_choice = os.getenv("MODEL_CHOICE", "gpt-4o-mini")
    
    # Limit content length to avoid token limits
    truncated_content = content[:15000] if len(content) > 15000 else content
    
    # Create the prompt for generating title and metadata
    prompt = f"""<source_content>
{truncated_content}
</source_content>

Analyze the above content from '{source_id}' and provide:

1. A concise, descriptive title (max 80 characters) that clearly describes what this resource is about. Examples:
   - "Pydantic AI API Reference"
   - "FastAPI Complete Guide" 
   - "React Component Library Documentation"
   - "Machine Learning Best Practices"

2. Determine the knowledge type: "technical" or "business"

3. Generate 3-7 relevant tags that categorize this content (e.g., python, ai, framework, documentation, tutorial, api, etc.)

4. Identify the primary category (e.g., documentation, tutorial, reference, guide, blog, paper)

5. If applicable, identify the programming language or technology focus

Respond in this exact JSON format:
{{
  "title": "Your generated title here",
  "knowledge_type": "technical",
  "tags": ["tag1", "tag2", "tag3"],
  "category": "documentation",
  "technology": "python",
  "difficulty": "beginner|intermediate|advanced"
}}"""
    
    try:
        # Call the OpenAI API to generate title and metadata
        response = client.chat.completions.create(
            model=model_choice,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes technical content and generates descriptive titles and metadata. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        # Parse the JSON response
        response_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        import json
        try:
            # Find JSON in the response (in case there's extra text)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
            else:
                result = json.loads(response_text)
            
            # Extract title and build metadata
            title = result.get("title", f"Content from {source_id}")
            metadata = {
                "knowledge_type": result.get("knowledge_type", knowledge_type),
                "tags": result.get("tags", tags),
                "category": result.get("category", "documentation"),
                "technology": result.get("technology"),
                "difficulty": result.get("difficulty"),
                "auto_generated": True,
                "generated_at": time.strftime("%Y-%m-%d")
            }
            
            # Remove None values
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            print(f"Generated title for {source_id}: {title}")
            
            # Add a small delay to prevent rate limiting when running in parallel
            time.sleep(0.3)  # Keep as time.sleep - this is in a sync function
            
            return title, metadata
            
        except json.JSONDecodeError as json_error:
            print(f"Error parsing JSON response for {source_id}: {json_error}")
            print(f"Response was: {response_text}")
            # Fallback to basic title and metadata
            return f"Content from {source_id}", {
                "knowledge_type": knowledge_type,
                "tags": tags,
                "auto_generated": False
            }
    
    except Exception as e:
        print(f"Error generating title/metadata with LLM for {source_id}: {e}")
        return f"Content from {source_id}", {
            "knowledge_type": knowledge_type,
            "tags": tags,
            "auto_generated": False
        }


def update_source_info(client: Client, source_id: str, summary: str, word_count: int, content: str = "", knowledge_type: str = "technical", tags: List[str] = None, update_frequency: int = 7):
    """
    Update or insert source information in the sources table with enhanced title and metadata.
    
    Args:
        client: Supabase client
        source_id: The source ID (domain)
        summary: Summary of the source
        word_count: Total word count for the source
        content: Full content for title/metadata generation
        knowledge_type: Type of knowledge (technical/business)
        tags: List of tags to include in metadata
        update_frequency: Update frequency in days (1=daily, 7=weekly, 30=monthly, 0=never)
    """
    if tags is None:
        tags = []
    
    # Generate enhanced title and metadata using LLM
    title, metadata = generate_source_title_and_metadata(
        source_id=source_id, 
        content=content,  # Pass content as keyword argument
        knowledge_type=knowledge_type,
        tags=tags
    )
    
    # Check if source already exists
    existing_source = client.from_('sources').select('source_id').eq('source_id', source_id).execute()
    
    source_data = {
        'source_id': source_id,
        'title': title,
        'summary': summary,
        'total_word_count': word_count,
        'metadata': metadata,
        'update_frequency': update_frequency,  # Store the update frequency
        'updated_at': 'now()'
    }
    
    if existing_source.data:
        # Update existing source
        result = client.from_('sources').update(source_data).eq('source_id', source_id).execute()
        print(f"Updated existing source: {source_id}")
    else:
        # Insert new source
        source_data['created_at'] = 'now()'
        result = client.from_('sources').insert(source_data).execute()
        print(f"Created new source: {source_id}")
    
    return result


def extract_source_summary(source_id: str, content: str, max_length: int = 500) -> str:
    """
    Extract a summary for a source from its content using an LLM.
    
    This function uses the OpenAI API to generate a concise summary of the source content.
    
    Args:
        source_id: The source ID (domain)
        content: the content to extract a summary from
        max_length: Maximum length of the summary
        
    Returns:
        A summary string
    """
    # Default summary if we can't extract anything meaningful
    default_summary = f"Content from {source_id}"
    
    if not content or len(content.strip()) == 0:
        return default_summary
    
    # Get the decrypted API key
    api_key = get_openai_api_key_sync()
    if not api_key:
        print(f"Error: No OpenAI API key available for source summary generation for {source_id}")
        return default_summary
    
    # Create OpenAI client with the decrypted key
    client = openai.OpenAI(api_key=api_key)
    
    # Get the model choice from environment variables
    model_choice = os.getenv("MODEL_CHOICE")
    
    # Limit content length to avoid token limits
    truncated_content = content[:25000] if len(content) > 25000 else content
    
    # Create the prompt for generating the summary
    prompt = f"""<source_content>
{truncated_content}
</source_content>

The above content is from the documentation for '{source_id}'. Please provide a concise summary (3-5 sentences) that describes what this library/tool/framework is about. The summary should help understand what the library/tool/framework accomplishes and the purpose.
"""
    
    try:
        # Call the OpenAI API to generate the summary
        response = client.chat.completions.create(
            model=model_choice,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise library/tool/framework summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        # Extract the generated summary
        summary = response.choices[0].message.content.strip()
        
        # Ensure the summary is not too long
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        # Add a small delay to prevent rate limiting when running in parallel
        time.sleep(0.3)  # Keep as time.sleep - this is in a sync function
            
        return summary
    
    except Exception as e:
        print(f"Error generating summary with LLM for {source_id}: {e}. Using default summary.")
        return default_summary


def search_code_examples(
    client: Client, 
    query: str, 
    match_count: int = 10, 
    filter_metadata: Optional[Dict[str, Any]] = None,
    source_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for code examples in Supabase using vector similarity.
    
    Args:
        client: Supabase client
        query: Query text
        match_count: Maximum number of results to return
        filter_metadata: Optional metadata filter
        source_id: Optional source ID to filter results
        
    Returns:
        List of matching code examples
    """
    # Create a more descriptive query for better embedding match
    # Since code examples are embedded with their summaries, we should make the query more descriptive
    enhanced_query = f"Code example for {query}\n\nSummary: Example code showing {query}"
    
    # Create embedding for the enhanced query
    query_embedding = create_embedding(enhanced_query)
    
    # Execute the search using the match_code_examples function
    try:
        # Only include filter parameter if filter_metadata is provided and not empty
        params = {
            'query_embedding': query_embedding,
            'match_count': match_count
        }
        
        # Only add the filter if it's actually provided and not empty
        if filter_metadata:
            params['filter'] = filter_metadata
            
        # Add source filter if provided
        if source_id:
            params['source_filter'] = source_id
        
        result = client.rpc('match_code_examples', params).execute()
        
        return result.data if result.data else []
    except Exception as e:
        print(f"Error searching code examples: {e}")
        return []
