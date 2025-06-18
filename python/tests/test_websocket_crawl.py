"""
Test script for WebSocket crawl progress improvements.

This script tests the enhanced WebSocket connection management for crawl progress.
"""

import asyncio
import json
import time
from datetime import datetime
import websockets
import httpx

# Configuration
BASE_URL = "http://localhost:8080"
WS_BASE_URL = "ws://localhost:8080"

async def test_crawl_with_websocket():
    """Test crawling with WebSocket progress tracking."""
    
    # Test URL to crawl
    test_url = "https://example.com"
    
    async with httpx.AsyncClient() as client:
        # Start crawl request
        print(f"[{datetime.now()}] Starting crawl request...")
        response = await client.post(
            f"{BASE_URL}/api/knowledge-items/crawl",
            json={
                "url": test_url,
                "knowledge_type": "technical",
                "tags": ["test", "websocket"],
                "update_frequency": 7
            }
        )
        
        if response.status_code != 200:
            print(f"Error starting crawl: {response.status_code} - {response.text}")
            return
        
        result = response.json()
        progress_id = result.get("progressId")
        
        if not progress_id:
            print("No progress ID returned!")
            return
        
        print(f"[{datetime.now()}] Got progress ID: {progress_id}")
        
        # Connect to WebSocket for progress
        ws_url = f"{WS_BASE_URL}/api/crawl-progress/{progress_id}"
        print(f"[{datetime.now()}] Connecting to WebSocket: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print(f"[{datetime.now()}] WebSocket connected!")
                
                # Send initial ping to verify connection
                await websocket.send("ping")
                
                # Listen for progress updates
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                        data = json.loads(message)
                        
                        if data.get("type") == "pong":
                            print(f"[{datetime.now()}] Received pong")
                            continue
                        
                        if data.get("type") == "heartbeat":
                            print(f"[{datetime.now()}] Received heartbeat")
                            continue
                        
                        if data.get("type") in ["crawl_progress", "crawl_completed", "crawl_error"]:
                            progress_data = data.get("data", {})
                            status = progress_data.get("status")
                            percentage = progress_data.get("percentage", 0)
                            log = progress_data.get("log", "")
                            
                            print(f"[{datetime.now()}] Progress: {status} - {percentage}% - {log}")
                            
                            if status == "completed":
                                print(f"[{datetime.now()}] Crawl completed successfully!")
                                chunks = progress_data.get("chunksStored", 0)
                                words = progress_data.get("wordCount", 0)
                                print(f"  Chunks stored: {chunks}")
                                print(f"  Words processed: {words}")
                                break
                            
                            if status == "error":
                                error = progress_data.get("error", "Unknown error")
                                print(f"[{datetime.now()}] Crawl failed: {error}")
                                break
                                
                    except asyncio.TimeoutError:
                        print(f"[{datetime.now()}] Timeout waiting for message")
                        break
                    except Exception as e:
                        print(f"[{datetime.now()}] Error: {e}")
                        break
                        
        except Exception as e:
            print(f"[{datetime.now()}] WebSocket connection error: {e}")

async def test_multiple_crawls():
    """Test multiple concurrent crawls."""
    
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://www.python.org/about/"
    ]
    
    tasks = []
    for url in urls:
        task = asyncio.create_task(test_single_crawl(url))
        tasks.append(task)
        # Small delay to avoid overwhelming the server
        await asyncio.sleep(0.5)
    
    # Wait for all crawls to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Crawl {i+1} failed: {result}")
        else:
            print(f"Crawl {i+1} completed")

async def test_single_crawl(url: str):
    """Test a single crawl operation."""
    
    async with httpx.AsyncClient() as client:
        # Start crawl
        response = await client.post(
            f"{BASE_URL}/api/knowledge-items/crawl",
            json={
                "url": url,
                "knowledge_type": "technical",
                "tags": ["test"],
                "update_frequency": 7
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to start crawl: {response.status_code}")
        
        result = response.json()
        progress_id = result.get("progressId")
        
        # Connect WebSocket and track progress
        ws_url = f"{WS_BASE_URL}/api/crawl-progress/{progress_id}"
        
        async with websockets.connect(ws_url) as websocket:
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=120.0)
                data = json.loads(message)
                
                if data.get("type") in ["crawl_completed", "crawl_error"]:
                    return data

async def main():
    """Main test runner."""
    
    print("=" * 60)
    print("WebSocket Crawl Progress Test")
    print("=" * 60)
    
    # Test 1: Single crawl with detailed progress
    print("\nTest 1: Single crawl with WebSocket progress")
    print("-" * 40)
    await test_crawl_with_websocket()
    
    # Wait a bit between tests
    await asyncio.sleep(2)
    
    # Test 2: Multiple concurrent crawls
    print("\n\nTest 2: Multiple concurrent crawls")
    print("-" * 40)
    await test_multiple_crawls()
    
    print("\n" + "=" * 60)
    print("All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())