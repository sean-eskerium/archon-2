"""
Crawling Service Module for Archon RAG

This module provides core crawling functionality that can be shared between
MCP tools and FastAPI endpoints. It handles web crawling operations including
single page crawling, batch crawling, and recursive crawling.
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urldefrag
from xml.etree import ElementTree
import requests
import traceback

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, MemoryAdaptiveDispatcher
from src.utils import get_supabase_client

logger = logging.getLogger(__name__)


class CrawlingService:
    """Service class for web crawling operations"""
    
    def __init__(self, crawler=None, supabase_client=None):
        """Initialize with optional crawler and supabase client"""
        self.crawler = crawler
        self.supabase_client = supabase_client or get_supabase_client()
    
    def is_sitemap(self, url: str) -> bool:
        """Check if a URL is a sitemap with error handling."""
        try:
            return url.endswith('sitemap.xml') or 'sitemap' in urlparse(url).path
        except Exception as e:
            logger.warning(f"Error checking if URL is sitemap: {e}")
            return False

    def is_txt(self, url: str) -> bool:
        """Check if a URL is a text file with error handling."""
        try:
            return url.endswith('.txt')
        except Exception as e:
            logger.warning(f"Error checking if URL is text file: {e}")
            return False

    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Parse a sitemap and extract URLs with comprehensive error handling."""
        urls = []
        
        try:
            logger.info(f"Parsing sitemap: {sitemap_url}")
            resp = requests.get(sitemap_url, timeout=30)
            
            if resp.status_code != 200:
                logger.error(f"Failed to fetch sitemap: HTTP {resp.status_code}")
                return urls
                
            try:
                tree = ElementTree.fromstring(resp.content)
                urls = [loc.text for loc in tree.findall('.//{*}loc') if loc.text]
                logger.info(f"Successfully extracted {len(urls)} URLs from sitemap")
                
            except ElementTree.ParseError as e:
                logger.error(f"Error parsing sitemap XML: {e}")
            except Exception as e:
                logger.error(f"Unexpected error parsing sitemap: {e}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching sitemap: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in sitemap parsing: {e}")
            logger.error(traceback.format_exc())

        return urls

    async def crawl_single_page(self, url: str, retry_count: int = 3) -> Dict[str, Any]:
        """
        Crawl a single web page and return the result with retry logic.
        
        Args:
            url: URL of the web page to crawl
            retry_count: Number of retry attempts
            
        Returns:
            Dict with success status, content, and metadata
        """
        last_error = None
        
        for attempt in range(retry_count):
            try:
                if not self.crawler:
                    return {
                        "success": False,
                        "error": "No crawler instance available"
                    }
                
                # Use ENABLED cache mode for better performance, BYPASS only on retries
                cache_mode = CacheMode.BYPASS if attempt > 0 else CacheMode.ENABLED
                crawl_config = CrawlerRunConfig(
                    cache_mode=cache_mode, 
                    stream=False,
                    wait_for="networkidle",  # Wait for network to be idle
                    timeout=30000  # 30 second timeout
                )
                
                logger.info(f"Crawling {url} (attempt {attempt + 1}/{retry_count})")
                result = await self.crawler.arun(url=url, config=crawl_config)
                
                if not result.success:
                    last_error = f"Failed to crawl {url}: {result.error_message}"
                    logger.warning(f"Crawl attempt {attempt + 1} failed: {last_error}")
                    
                    # Exponential backoff before retry
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2 ** attempt)
                    continue
                
                # Validate content
                if not result.markdown or len(result.markdown.strip()) < 50:
                    last_error = f"Insufficient content from {url}"
                    logger.warning(f"Crawl attempt {attempt + 1}: {last_error}")
                    
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2 ** attempt)
                    continue
                
                # Success!
                return {
                    "success": True,
                    "url": url,
                    "markdown": result.markdown,
                    "title": result.title or "Untitled",
                    "links": result.links,
                    "content_length": len(result.markdown)
                }
                
            except asyncio.TimeoutError:
                last_error = f"Timeout crawling {url}"
                logger.warning(f"Crawl attempt {attempt + 1} timed out")
            except Exception as e:
                last_error = f"Error crawling page: {str(e)}"
                logger.error(f"Error on attempt {attempt + 1} crawling {url}: {e}")
                logger.error(traceback.format_exc())
            
            # Exponential backoff before retry
            if attempt < retry_count - 1:
                await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        return {
            "success": False,
            "error": last_error or f"Failed to crawl {url} after {retry_count} attempts"
        }

    async def crawl_markdown_file(self, url: str) -> List[Dict[str, Any]]:
        """Crawl a .txt or markdown file with comprehensive error handling."""
        try:
            logger.info(f"Crawling markdown file: {url}")
            crawl_config = CrawlerRunConfig()

            result = await self.crawler.arun(url=url, config=crawl_config)
            if result.success and result.markdown:
                logger.info(f"Successfully crawled markdown file: {url}")
                return [{'url': url, 'markdown': result.markdown}]
            else:
                logger.error(f"Failed to crawl {url}: {result.error_message}")
                return []
        except Exception as e:
            logger.error(f"Exception while crawling markdown file {url}: {e}")
            logger.error(traceback.format_exc())
            return []

    async def crawl_batch_with_progress(self, urls: List[str], max_concurrent: int = 10, 
                                       progress_callback=None, start_progress: int = 15, 
                                       end_progress: int = 60) -> List[Dict[str, Any]]:
        """Batch crawl multiple URLs in parallel with progress reporting."""
        crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)
        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=70.0,
            check_interval=1.0,
            max_session_permit=max_concurrent
        )

        async def report_progress(percentage: int, message: str):
            """Helper to report progress if callback is available"""
            if progress_callback:
                await progress_callback('crawling', percentage, message)

        total_urls = len(urls)
        await report_progress(start_progress, f'Starting to crawl {total_urls} URLs...')
        
        # Process URLs in smaller batches for better progress reporting and reliability
        batch_size = min(10, max_concurrent)  # Reduced from 20 to 10 for better reliability
        successful_results = []
        processed = 0
        
        for i in range(0, total_urls, batch_size):
            batch_urls = urls[i:i + batch_size]
            batch_start = i
            batch_end = min(i + batch_size, total_urls)
            
            # Report batch start
            progress_percentage = start_progress + int((processed / total_urls) * (end_progress - start_progress))
            await report_progress(progress_percentage, f'Processing batch {batch_start+1}-{batch_end} of {total_urls} URLs...')
            
            # Crawl this batch
            batch_results = await self.crawler.arun_many(urls=batch_urls, config=crawl_config, dispatcher=dispatcher)
            
            # Process batch results
            for result in batch_results:
                processed += 1
                if result.success and result.markdown:
                    successful_results.append({'url': result.url, 'markdown': result.markdown})
                
                # Report individual URL progress
                progress_percentage = start_progress + int((processed / total_urls) * (end_progress - start_progress))
                if processed % 10 == 0 or processed == total_urls:  # Report every 10 URLs or at the end
                    await report_progress(progress_percentage, f'Crawled {processed}/{total_urls} pages ({len(successful_results)} successful)')
        
        await report_progress(end_progress, f'Batch crawling completed: {len(successful_results)}/{total_urls} pages successful')
        return successful_results

    async def crawl_recursive_with_progress(self, start_urls: List[str], max_depth: int = 3, 
                                          max_concurrent: int = 10, progress_callback=None, 
                                          start_progress: int = 10, end_progress: int = 60) -> List[Dict[str, Any]]:
        """Recursively crawl internal links from start URLs up to a maximum depth with progress reporting."""
        run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)
        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=70.0,
            check_interval=1.0,
            max_session_permit=max_concurrent
        )

        async def report_progress(percentage: int, message: str, **kwargs):
            """Helper to report progress if callback is available"""
            if progress_callback:
                # Add step information for multi-progress tracking
                step_info = {
                    'currentStep': message,
                    'stepMessage': message,
                    **kwargs
                }
                await progress_callback('crawling', percentage, message, **step_info)

        visited = set()

        def normalize_url(url):
            return urldefrag(url)[0]

        current_urls = set([normalize_url(u) for u in start_urls])
        results_all = []
        total_processed = 0

        for depth in range(max_depth):
            urls_to_crawl = [normalize_url(url) for url in current_urls if normalize_url(url) not in visited]
            if not urls_to_crawl:
                break

            # Calculate progress for this depth level
            depth_start = start_progress + int((depth / max_depth) * (end_progress - start_progress) * 0.8)
            depth_end = start_progress + int(((depth + 1) / max_depth) * (end_progress - start_progress) * 0.8)
            
            await report_progress(depth_start, f'Crawling depth {depth + 1}/{max_depth}: {len(urls_to_crawl)} URLs to process')

            # Process URLs in smaller batches for better progress reporting
            batch_size = min(20, max_concurrent)  # Process in batches of 20
            next_level_urls = set()
            depth_successful = 0
            
            for batch_idx in range(0, len(urls_to_crawl), batch_size):
                batch_urls = urls_to_crawl[batch_idx:batch_idx + batch_size]
                batch_end_idx = min(batch_idx + batch_size, len(urls_to_crawl))
                
                # Calculate progress for this batch within the depth
                batch_progress = depth_start + int((batch_idx / len(urls_to_crawl)) * (depth_end - depth_start))
                await report_progress(batch_progress, 
                                    f'Depth {depth + 1}: crawling URLs {batch_idx + 1}-{batch_end_idx} of {len(urls_to_crawl)}',
                                    totalPages=total_processed + batch_idx, 
                                    processedPages=len(results_all))
                
                # Crawl this batch
                batch_results = await self.crawler.arun_many(urls=batch_urls, config=run_config, dispatcher=dispatcher)
                
                # Process each result in the batch
                for i, result in enumerate(batch_results):
                    norm_url = normalize_url(result.url)
                    visited.add(norm_url)
                    total_processed += 1
                    
                    if result.success and result.markdown:
                        results_all.append({'url': result.url, 'markdown': result.markdown})
                        depth_successful += 1
                        
                        # Find internal links for next depth
                        for link in result.links.get("internal", []):
                            next_url = normalize_url(link["href"])
                            if next_url not in visited:
                                next_level_urls.add(next_url)
                    
                    # Report progress every few URLs
                    current_idx = batch_idx + i + 1
                    if current_idx % 5 == 0 or current_idx == len(urls_to_crawl):
                        current_progress = depth_start + int((current_idx / len(urls_to_crawl)) * (depth_end - depth_start))
                        await report_progress(current_progress,
                                            f'Depth {depth + 1}: processed {current_idx}/{len(urls_to_crawl)} URLs ({depth_successful} successful)',
                                            totalPages=total_processed, 
                                            processedPages=len(results_all))

            current_urls = next_level_urls
            
            # Report completion of this depth
            await report_progress(depth_end, 
                                f'Depth {depth + 1} completed: {depth_successful} pages crawled, {len(next_level_urls)} URLs found for next depth')

        await report_progress(end_progress, f'Recursive crawling completed: {len(results_all)} total pages crawled across {max_depth} depth levels')
        return results_all