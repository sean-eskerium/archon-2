"""Mock data factories for testing.

This module provides factory functions and fixtures for generating test data.
Uses factory patterns for flexible and customizable test data generation.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
import random
import string


class IDGenerator:
    """Generate unique IDs for test data."""
    
    _counters = {}
    
    @classmethod
    def generate(cls, prefix: str) -> str:
        """Generate a unique ID with the given prefix."""
        if prefix not in cls._counters:
            cls._counters[prefix] = 0
        cls._counters[prefix] += 1
        return f"{prefix}_{cls._counters[prefix]}_{uuid4().hex[:8]}"
    
    @classmethod
    def reset(cls):
        """Reset all counters."""
        cls._counters.clear()


class ProjectFactory:
    """Factory for creating project test data."""
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a project with default values and overrides."""
        now = datetime.utcnow()
        
        defaults = {
            "id": IDGenerator.generate("proj"),
            "name": f"Test Project {random.randint(1, 1000)}",
            "description": "A test project for automated testing",
            "status": random.choice(["active", "archived", "draft"]),
            "metadata": {
                "created_by": "test_user",
                "tags": ["test", "automated"],
                "version": "1.0.0"
            },
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        # Deep merge kwargs into defaults
        result = defaults.copy()
        if "metadata" in kwargs and "metadata" in result:
            result["metadata"] = {**result["metadata"], **kwargs.pop("metadata")}
        result.update(kwargs)
        
        return result
    
    @staticmethod
    def create_batch(count: int, **common_kwargs) -> List[Dict[str, Any]]:
        """Create multiple projects with common attributes."""
        return [
            ProjectFactory.create(
                name=f"Batch Project {i+1}",
                **common_kwargs
            )
            for i in range(count)
        ]


class TaskFactory:
    """Factory for creating task test data."""
    
    TASK_TITLES = [
        "Implement user authentication",
        "Design database schema",
        "Create API endpoints",
        "Write unit tests",
        "Setup CI/CD pipeline",
        "Optimize performance",
        "Update documentation",
        "Fix security vulnerabilities",
        "Refactor legacy code",
        "Deploy to production"
    ]
    
    @staticmethod
    def create(project_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a task with default values and overrides."""
        now = datetime.utcnow()
        due_date = now + timedelta(days=random.randint(1, 30))
        
        defaults = {
            "id": IDGenerator.generate("task"),
            "project_id": project_id or IDGenerator.generate("proj"),
            "title": random.choice(TaskFactory.TASK_TITLES),
            "description": "Task description with more details about the work to be done.",
            "status": random.choice(["todo", "in_progress", "done", "archived"]),
            "priority": random.choice(["low", "medium", "high", "critical"]),
            "assignee": random.choice(["user1", "user2", "user3", None]),
            "due_date": due_date.isoformat() if random.random() > 0.3 else None,
            "labels": random.sample(["bug", "feature", "enhancement", "documentation", "testing"], k=random.randint(0, 3)),
            "parent_id": None,
            "subtasks": [],
            "metadata": {
                "estimated_hours": random.randint(1, 40),
                "actual_hours": None,
                "blocked": False,
                "blockers": []
            },
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        # Deep merge kwargs
        result = defaults.copy()
        if "metadata" in kwargs and "metadata" in result:
            result["metadata"] = {**result["metadata"], **kwargs.pop("metadata")}
        result.update(kwargs)
        
        return result
    
    @staticmethod
    def create_subtasks(parent_task_id: str, count: int = 3) -> List[Dict[str, Any]]:
        """Create subtasks for a parent task."""
        parent_project_id = f"proj_{parent_task_id.split('_')[1]}"
        return [
            TaskFactory.create(
                project_id=parent_project_id,
                parent_id=parent_task_id,
                title=f"Subtask {i+1}: {random.choice(['Research', 'Implementation', 'Testing', 'Review'])}",
                priority="medium"
            )
            for i in range(count)
        ]


class DocumentFactory:
    """Factory for creating document test data."""
    
    DOCUMENT_TITLES = [
        "Project Requirements Document",
        "Technical Specification",
        "API Documentation",
        "User Guide",
        "Architecture Overview",
        "Meeting Notes",
        "Design Decisions",
        "Test Plan",
        "Release Notes",
        "Security Assessment"
    ]
    
    @staticmethod
    def create(project_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a document with default values and overrides."""
        now = datetime.utcnow()
        
        # Generate some fake content
        paragraphs = [
            "This document describes the key aspects of the system architecture and implementation details.",
            "The proposed solution addresses all the requirements outlined in the project specification.",
            "Performance benchmarks indicate that the system can handle the expected load with minimal latency.",
            "Security measures have been implemented according to industry best practices and compliance requirements.",
            "Future enhancements and scalability considerations are documented in the appendix section."
        ]
        
        defaults = {
            "id": IDGenerator.generate("doc"),
            "project_id": project_id or IDGenerator.generate("proj"),
            "title": random.choice(DocumentFactory.DOCUMENT_TITLES),
            "content": {
                "type": "markdown",
                "text": "\n\n".join(random.sample(paragraphs, k=random.randint(2, 4))),
                "sections": [
                    {"title": "Introduction", "content": paragraphs[0]},
                    {"title": "Implementation", "content": paragraphs[1]},
                    {"title": "Conclusion", "content": paragraphs[4]}
                ]
            },
            "version": 1,
            "metadata": {
                "author": random.choice(["user1", "user2", "user3"]),
                "tags": random.sample(["draft", "review", "approved", "technical", "user-facing"], k=2),
                "word_count": random.randint(500, 5000),
                "reading_time_minutes": random.randint(2, 20)
            },
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        # Deep merge kwargs
        result = defaults.copy()
        if "metadata" in kwargs and "metadata" in result:
            result["metadata"] = {**result["metadata"], **kwargs.pop("metadata")}
        if "content" in kwargs and "content" in result:
            result["content"] = {**result["content"], **kwargs.pop("content")}
        result.update(kwargs)
        
        return result
    
    @staticmethod
    def create_version_history(document_id: str, versions: int = 3) -> List[Dict[str, Any]]:
        """Create version history for a document."""
        base_time = datetime.utcnow() - timedelta(days=versions * 7)
        history = []
        
        for v in range(1, versions + 1):
            version_time = base_time + timedelta(days=v * 7)
            history.append({
                "version": v,
                "document_id": document_id,
                "changes": {
                    "added": random.randint(10, 100),
                    "removed": random.randint(5, 50),
                    "modified": random.randint(20, 200)
                },
                "author": random.choice(["user1", "user2", "user3"]),
                "message": f"Version {v} - {random.choice(['Major update', 'Minor fixes', 'Content revision', 'Formatting changes'])}",
                "created_at": version_time.isoformat()
            })
        
        return history


class KnowledgeSourceFactory:
    """Factory for creating knowledge source test data."""
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a knowledge source with default values and overrides."""
        now = datetime.utcnow()
        source_types = ["url", "file", "api", "database"]
        source_type = kwargs.get("type", random.choice(source_types))
        
        defaults = {
            "id": IDGenerator.generate("ks"),
            "name": f"Knowledge Source {random.randint(1, 100)}",
            "type": source_type,
            "url": f"https://example.com/source/{random.randint(1, 1000)}" if source_type == "url" else None,
            "file_path": f"/data/sources/file_{random.randint(1, 100)}.pdf" if source_type == "file" else None,
            "config": {
                "crawl_depth": random.randint(1, 3),
                "include_images": random.choice([True, False]),
                "max_pages": random.randint(10, 100),
                "update_frequency": random.choice(["daily", "weekly", "monthly"])
            },
            "status": random.choice(["active", "inactive", "processing", "error"]),
            "last_crawled": (now - timedelta(hours=random.randint(1, 168))).isoformat(),
            "metadata": {
                "total_documents": random.randint(10, 1000),
                "total_chunks": random.randint(100, 10000),
                "avg_chunk_size": random.randint(100, 500),
                "last_error": None
            },
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        # Deep merge kwargs
        result = defaults.copy()
        for key in ["config", "metadata"]:
            if key in kwargs and key in result:
                result[key] = {**result[key], **kwargs.pop(key)}
        result.update(kwargs)
        
        return result


class ChatMessageFactory:
    """Factory for creating chat message test data."""
    
    USER_MESSAGES = [
        "Can you help me understand this concept?",
        "What are the best practices for this implementation?",
        "How do I fix this error?",
        "Can you explain the architecture?",
        "What's the difference between these approaches?",
        "Is this the correct way to implement this feature?",
        "Can you review my code?",
        "What security considerations should I keep in mind?",
        "How can I optimize this for better performance?",
        "What testing strategies would you recommend?"
    ]
    
    ASSISTANT_MESSAGES = [
        "I'd be happy to help you with that. Here's what you need to know...",
        "Great question! Let me break this down for you...",
        "Based on your requirements, I recommend the following approach...",
        "Here's a step-by-step solution to your problem...",
        "Let me explain the key concepts and best practices...",
        "I've analyzed your code and here are my suggestions...",
        "From a security perspective, you should consider...",
        "To optimize performance, you could try...",
        "For comprehensive testing, I suggest...",
        "The architecture follows these principles..."
    ]
    
    @staticmethod
    def create(role: str = "user", **kwargs) -> Dict[str, Any]:
        """Create a chat message with default values and overrides."""
        now = datetime.utcnow()
        
        defaults = {
            "id": IDGenerator.generate("msg"),
            "role": role,
            "content": random.choice(
                ChatMessageFactory.USER_MESSAGES if role == "user" 
                else ChatMessageFactory.ASSISTANT_MESSAGES
            ),
            "metadata": {
                "model": "gpt-4" if role == "assistant" else None,
                "tokens": random.randint(10, 500) if role == "assistant" else None,
                "processing_time": random.uniform(0.1, 2.0) if role == "assistant" else None,
                "sources": [] if role == "assistant" else None
            },
            "created_at": now.isoformat(),
        }
        
        # Deep merge kwargs
        result = defaults.copy()
        if "metadata" in kwargs and "metadata" in result:
            result["metadata"] = {**result["metadata"], **kwargs.pop("metadata")}
        result.update(kwargs)
        
        return result
    
    @staticmethod
    def create_conversation(messages: int = 6) -> List[Dict[str, Any]]:
        """Create a conversation with alternating user/assistant messages."""
        conversation = []
        
        for i in range(messages):
            role = "user" if i % 2 == 0 else "assistant"
            message = ChatMessageFactory.create(role=role)
            
            # Add context references for assistant messages
            if role == "assistant" and i > 0:
                message["metadata"]["references"] = [
                    conversation[i-1]["id"]  # Reference to previous user message
                ]
            
            conversation.append(message)
        
        return conversation


class MCPToolFactory:
    """Factory for creating MCP tool test data."""
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create an MCP tool definition."""
        tool_names = [
            "search_documents",
            "create_task",
            "update_project",
            "run_analysis",
            "generate_report",
            "execute_query"
        ]
        
        defaults = {
            "name": kwargs.get("name", random.choice(tool_names)),
            "description": "A test tool for MCP operations",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "count": {"type": "integer"}
                }
            }
        }
        
        result = defaults.copy()
        result.update(kwargs)
        return result


class SearchResultFactory:
    """Factory for creating search result test data."""
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a search result."""
        now = datetime.utcnow()
        
        defaults = {
            "id": IDGenerator.generate("result"),
            "content": "This is a relevant piece of content that matches the search query with high confidence.",
            "metadata": {
                "source": random.choice(["document", "website", "database", "api"]),
                "source_id": IDGenerator.generate("source"),
                "title": "Relevant Document Title",
                "url": f"https://example.com/doc/{random.randint(1, 1000)}",
                "author": random.choice(["Author 1", "Author 2", "Author 3"]),
                "created_date": (now - timedelta(days=random.randint(1, 365))).isoformat()
            },
            "score": random.uniform(0.7, 1.0),
            "highlights": [
                "This is a <em>relevant</em> piece of content",
                "matches the <em>search query</em> with high confidence"
            ]
        }
        
        # Deep merge kwargs
        result = defaults.copy()
        if "metadata" in kwargs and "metadata" in result:
            result["metadata"] = {**result["metadata"], **kwargs.pop("metadata")}
        result.update(kwargs)
        
        return result
    
    @staticmethod
    def create_results(count: int = 5, **common_kwargs) -> List[Dict[str, Any]]:
        """Create multiple search results with decreasing scores."""
        results = []
        base_score = 0.95
        
        for i in range(count):
            score = base_score - (i * 0.05)
            result = SearchResultFactory.create(
                score=max(score, 0.5),
                **common_kwargs
            )
            results.append(result)
        
        return results


# Utility functions for test data generation

def generate_random_string(length: int = 10) -> str:
    """Generate a random string of specified length."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_email() -> str:
    """Generate a random email address."""
    username = generate_random_string(8)
    domain = random.choice(["example.com", "test.com", "demo.org"])
    return f"{username}@{domain}"


def generate_random_url() -> str:
    """Generate a random URL."""
    protocol = random.choice(["http", "https"])
    domain = random.choice(["example.com", "test.org", "demo.net"])
    path = '/'.join([generate_random_string(5) for _ in range(random.randint(1, 3))])
    return f"{protocol}://{domain}/{path}"


def generate_random_json() -> Dict[str, Any]:
    """Generate random JSON-like data."""
    return {
        "string": generate_random_string(),
        "number": random.randint(1, 1000),
        "float": random.uniform(0.0, 100.0),
        "boolean": random.choice([True, False]),
        "array": [generate_random_string(5) for _ in range(random.randint(1, 5))],
        "nested": {
            "value": generate_random_string(),
            "count": random.randint(1, 100)
        }
    }


# Test data sets for comprehensive testing

def create_test_project_hierarchy() -> Dict[str, Any]:
    """Create a complete project hierarchy with tasks and documents."""
    project = ProjectFactory.create(name="Test Project Hierarchy")
    
    # Create main tasks
    tasks = []
    for i in range(5):
        task = TaskFactory.create(
            project_id=project["id"],
            title=f"Main Task {i+1}",
            priority="high" if i < 2 else "medium"
        )
        
        # Create subtasks for some tasks
        if i < 3:
            subtasks = TaskFactory.create_subtasks(task["id"], count=random.randint(2, 4))
            task["subtasks"] = subtasks
            tasks.extend(subtasks)
        
        tasks.append(task)
    
    # Create documents
    documents = []
    for i in range(3):
        doc = DocumentFactory.create(
            project_id=project["id"],
            title=f"Project Document {i+1}"
        )
        
        # Create version history for first document
        if i == 0:
            doc["versions"] = DocumentFactory.create_version_history(doc["id"])
        
        documents.append(doc)
    
    return {
        "project": project,
        "tasks": tasks,
        "documents": documents
    }


def create_test_knowledge_base() -> Dict[str, Any]:
    """Create a test knowledge base with sources and search results."""
    sources = [
        KnowledgeSourceFactory.create(type="url", name="Documentation Site"),
        KnowledgeSourceFactory.create(type="file", name="Technical Specs PDF"),
        KnowledgeSourceFactory.create(type="api", name="External API"),
    ]
    
    # Create search results from these sources
    all_results = []
    for source in sources:
        results = SearchResultFactory.create_results(
            count=random.randint(3, 7),
            metadata={"source_id": source["id"], "source": source["type"]}
        )
        all_results.extend(results)
    
    return {
        "sources": sources,
        "search_results": all_results
    }


def create_test_chat_session() -> Dict[str, Any]:
    """Create a test chat session with conversation and context."""
    conversation = ChatMessageFactory.create_conversation(messages=8)
    
    # Add search results as context for some assistant messages
    for i, msg in enumerate(conversation):
        if msg["role"] == "assistant" and i > 2:
            search_results = SearchResultFactory.create_results(count=3)
            msg["metadata"]["sources"] = [r["id"] for r in search_results]
            msg["context"] = search_results
    
    return {
        "session_id": IDGenerator.generate("session"),
        "messages": conversation,
        "metadata": {
            "total_tokens": sum(m.get("metadata", {}).get("tokens", 0) for m in conversation),
            "duration": sum(m.get("metadata", {}).get("processing_time", 0) for m in conversation),
            "model": "gpt-4"
        }
    }


# Reset function for test isolation

def reset_test_data():
    """Reset all test data counters and caches."""
    IDGenerator.reset()