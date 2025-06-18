
/**
 * Knowledge Base service for managing documentation sources
 */

import { crawlSinglePage, smartCrawlUrl, uploadDocument as apiUploadDocument } from './api'

// Types
export interface KnowledgeItemMetadata {
  knowledge_type?: 'technical' | 'business'
  tags?: string[]
  source_type?: 'url' | 'file'
  status?: 'active' | 'processing' | 'error'
  description?: string
  last_scraped?: string
  chunks_count?: number
  word_count?: number
  file_name?: string
  file_type?: string
  page_count?: number
  update_frequency?: number
  next_update?: string
}

export interface KnowledgeItem {
  id: string
  title: string
  url: string
  source_id: string
  metadata: KnowledgeItemMetadata
  created_at: string
  updated_at: string
}

export interface KnowledgeItemsResponse {
  items: KnowledgeItem[]
  total: number
  page: number
  per_page: number
}

export interface KnowledgeItemsFilter {
  knowledge_type?: 'technical' | 'business'
  tags?: string[]
  source_type?: 'url' | 'file'
  search?: string
  page?: number
  per_page?: number
}

export interface CrawlRequest {
  url: string
  knowledge_type?: 'technical' | 'business'
  tags?: string[]
  update_frequency?: number
  max_depth?: number
  crawl_options?: {
    max_concurrent?: number
  }
}

export interface UploadMetadata {
  knowledge_type?: 'technical' | 'business'
  tags?: string[]
}

export interface SearchOptions {
  knowledge_type?: 'technical' | 'business'
  sources?: string[]
  limit?: number
}

// Dynamic API base URL that works with different hosts
const getApiBaseUrl = () => {
  const protocol = window.location.protocol;
  const host = window.location.hostname;
  const port = '8080'; // Backend API port
  return `${protocol}//${host}:${port}/api`;
};

const API_BASE_URL = getApiBaseUrl();

// Helper function for API requests
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || `HTTP ${response.status}`)
  }

  return response.json()
}

class KnowledgeBaseService {
  /**
   * Get knowledge items with optional filtering
   */
  async getKnowledgeItems(filter: KnowledgeItemsFilter = {}): Promise<KnowledgeItemsResponse> {
    const params = new URLSearchParams()
    
    // Add default pagination
    params.append('page', String(filter.page || 1))
    params.append('per_page', String(filter.per_page || 20))
    
    // Add optional filters
    if (filter.knowledge_type) params.append('knowledge_type', filter.knowledge_type)
    if (filter.tags && filter.tags.length > 0) params.append('tags', filter.tags.join(','))
    if (filter.source_type) params.append('source_type', filter.source_type)
    if (filter.search) params.append('search', filter.search)
    
    return apiRequest<KnowledgeItemsResponse>(`/knowledge-items?${params}`)
  }

  /**
   * Delete a knowledge item by source_id
   */
  async deleteKnowledgeItem(sourceId: string) {
    return apiRequest(`/knowledge-items/${sourceId}`, {
      method: 'DELETE'
    })
  }

  /**
   * Update knowledge item metadata
   */
  async updateKnowledgeItem(sourceId: string, updates: Partial<KnowledgeItemMetadata>) {
    return apiRequest(`/knowledge-items/${sourceId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    })
  }

  /**
   * Upload a document to the knowledge base with progress tracking
   */
  async uploadDocument(file: File, metadata: UploadMetadata = {}) {
    const formData = new FormData()
    formData.append('file', file)
    
    // Send fields as expected by backend API
    if (metadata.knowledge_type) {
      formData.append('knowledge_type', metadata.knowledge_type)
    }
    if (metadata.tags && metadata.tags.length > 0) {
      formData.append('tags', JSON.stringify(metadata.tags))
    }
    
    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || `HTTP ${response.status}`)
    }

    return response.json()
  }

  /**
   * Start crawling a URL with metadata
   */
  async crawlUrl(request: CrawlRequest) {
    console.log('📡 Sending crawl request:', request);
    
    const response = await apiRequest('/knowledge-items/crawl', {
      method: 'POST',
      body: JSON.stringify(request)
    });
    
    console.log('📡 Crawl response received:', response);
    console.log('📡 Response type:', typeof response);
    console.log('📡 Response has progressId?', 'progressId' in (response as any));
    
    return response;
  }

  /**
   * Get detailed information about a knowledge item
   */
  async getKnowledgeItemDetails(sourceId: string) {
    return apiRequest(`/knowledge-items/${sourceId}/details`)
  }

  /**
   * Search across the knowledge base
   */
  async searchKnowledgeBase(query: string, options: SearchOptions = {}) {
    return apiRequest('/knowledge-items/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        ...options
      })
    })
  }
}

// Export singleton instance
export const knowledgeBaseService = new KnowledgeBaseService() 