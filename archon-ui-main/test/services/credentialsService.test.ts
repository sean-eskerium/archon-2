import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import { credentialsService } from '@/services/credentialsService'
import type { Credential, RagSettings } from '@/services/credentialsService'

// Mock fetch globally
(globalThis as any).fetch = vi.fn()

describe('credentialsService', () => {
  let mockFetch: ReturnType<typeof vi.fn>
  const baseUrl = 'http://localhost:8080'
  
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch = vi.mocked((globalThis as any).fetch)
    // Clear localStorage
    global.localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Credential Fetching', () => {
    it('should fetch all credentials from API endpoint', async () => {
      const mockCredentials: Credential[] = [
        {
          key: 'OPENAI_API_KEY',
          value: 'sk-test123',
          is_encrypted: false,
          category: 'api_keys'
        },
        {
          key: 'GITHUB_TOKEN',
          value: 'ghp_test456',
          is_encrypted: false,
          category: 'api_keys'
        }
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCredentials
      })

      const credentials = await credentialsService.getAllCredentials()

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/credentials`)
      expect(credentials).toEqual(mockCredentials)
    })

    it('should fetch credentials by category', async () => {
      const mockResponse = {
        credentials: {
          OPENAI_API_KEY: {
            value: 'sk-test123',
            is_encrypted: false,
            description: 'OpenAI API Key'
          },
          ANTHROPIC_API_KEY: {
            encrypted_value: 'encrypted_value_here',
            is_encrypted: true,
            description: 'Anthropic API Key'
          }
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const credentials = await credentialsService.getCredentialsByCategory('api_keys')

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/credentials/categories/api_keys`)
      expect(credentials).toHaveLength(2)
      expect(credentials[0]).toMatchObject({
        key: 'OPENAI_API_KEY',
        value: 'sk-test123',
        is_encrypted: false,
        category: 'api_keys'
      })
      expect(credentials[1]).toMatchObject({
        key: 'ANTHROPIC_API_KEY',
        encrypted_value: 'encrypted_value_here',
        is_encrypted: true,
        category: 'api_keys'
      })
    })

    it('should handle individual credential fetch', async () => {
      const mockCredential = {
        key: 'OPENAI_API_KEY',
        value: 'sk-test123',
        is_encrypted: false
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCredential
      })

      const credential = await credentialsService.getCredential('OPENAI_API_KEY')

      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/credentials/OPENAI_API_KEY`)
      expect(credential).toEqual(mockCredential)
    })

    it('should handle missing credential gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404
      })

      const credential = await credentialsService.getCredential('NON_EXISTENT_KEY')

      expect(credential).toEqual({
        key: 'NON_EXISTENT_KEY',
        value: undefined
      })
    })
  })

  describe('RAG Settings', () => {
    it('should fetch and parse RAG settings correctly', async () => {
      const mockRagCredentials = {
        credentials: {
          USE_CONTEXTUAL_EMBEDDINGS: { value: 'true', is_encrypted: false },
          CONTEXTUAL_EMBEDDINGS_MAX_WORKERS: { value: '5', is_encrypted: false },
          USE_HYBRID_SEARCH: { value: 'false', is_encrypted: false },
          USE_AGENTIC_RAG: { value: 'true', is_encrypted: false },
          USE_RERANKING: { value: 'false', is_encrypted: false }
        }
      }

      const mockApiKeysCredentials = {
        credentials: {
          MODEL_CHOICE: { value: 'gpt-4-turbo', is_encrypted: false }
        }
      }

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockRagCredentials
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockApiKeysCredentials
        })

      const settings = await credentialsService.getRagSettings()

      expect(settings).toEqual({
        USE_CONTEXTUAL_EMBEDDINGS: true,
        CONTEXTUAL_EMBEDDINGS_MAX_WORKERS: 5,
        USE_HYBRID_SEARCH: false,
        USE_AGENTIC_RAG: true,
        USE_RERANKING: false,
        MODEL_CHOICE: 'gpt-4-turbo'
      })
    })

    it('should use default values for missing RAG settings', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ credentials: {} })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ credentials: {} })
        })

      const settings = await credentialsService.getRagSettings()

      expect(settings).toEqual({
        USE_CONTEXTUAL_EMBEDDINGS: false,
        CONTEXTUAL_EMBEDDINGS_MAX_WORKERS: 3,
        USE_HYBRID_SEARCH: false,
        USE_AGENTIC_RAG: false,
        USE_RERANKING: false,
        MODEL_CHOICE: 'gpt-4.1-nano'
      })
    })

    it('should update RAG settings with multiple API calls', async () => {
      const settings: RagSettings = {
        USE_CONTEXTUAL_EMBEDDINGS: true,
        CONTEXTUAL_EMBEDDINGS_MAX_WORKERS: 8,
        USE_HYBRID_SEARCH: true,
        USE_AGENTIC_RAG: false,
        USE_RERANKING: true,
        MODEL_CHOICE: 'claude-3-sonnet'
      }

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true })
      })

      await credentialsService.updateRagSettings(settings)

      // Should make 6 API calls (one for each setting)
      expect(mockFetch).toHaveBeenCalledTimes(6)
      
      // Verify each setting is sent correctly
      const calls = mockFetch.mock.calls
      const bodies = calls.map((call: any) => JSON.parse(call[1]?.body as string))
      
      expect(bodies).toContainEqual(
        expect.objectContaining({
          key: 'USE_CONTEXTUAL_EMBEDDINGS',
          value: 'true',
          category: 'rag_strategy'
        })
      )
      
      expect(bodies).toContainEqual(
        expect.objectContaining({
          key: 'MODEL_CHOICE',
          value: 'claude-3-sonnet',
          category: 'rag_strategy'
        })
      )
    })
  })

  describe('Credential CRUD Operations', () => {
    it('should create a new credential', async () => {
      const newCredential: Credential = {
        key: 'NEW_API_KEY',
        value: 'test-value-123',
        is_encrypted: false,
        category: 'api_keys',
        description: 'New API Key'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...newCredential, id: 'cred-123' })
      })

      const result = await credentialsService.createCredential(newCredential)

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/credentials`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newCredential)
        }
      )
      expect(result).toHaveProperty('id', 'cred-123')
    })

    it('should update an existing credential', async () => {
      const credential: Credential = {
        key: 'OPENAI_API_KEY',
        value: 'sk-updated-key',
        is_encrypted: false,
        category: 'api_keys'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...credential, updated_at: new Date().toISOString() })
      })

      const result = await credentialsService.updateCredential(credential)

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/credentials/OPENAI_API_KEY`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(credential)
        }
      )
      expect(result).toHaveProperty('updated_at')
    })

    it('should delete a credential', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      })

      await credentialsService.deleteCredential('OLD_API_KEY')

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/credentials/OLD_API_KEY`,
        { method: 'DELETE' }
      )
    })
  })

  describe('Error Handling', () => {
    test.each([
      {
        method: 'getAllCredentials',
        errorMessage: 'Failed to fetch credentials'
      },
      {
        method: 'getCredentialsByCategory',
        args: ['api_keys'],
        errorMessage: 'Failed to fetch credentials for category: api_keys'
      },
      {
        method: 'updateCredential',
        args: [{ key: 'TEST', value: 'test', is_encrypted: false, category: 'test' }],
        errorMessage: 'Failed to update credential'
      },
      {
        method: 'createCredential',
        args: [{ key: 'TEST', value: 'test', is_encrypted: false, category: 'test' }],
        errorMessage: 'Failed to create credential'
      },
      {
        method: 'deleteCredential',
        args: ['TEST'],
        errorMessage: 'Failed to delete credential'
      }
    ])('should handle $method errors', async ({ method, args = [], errorMessage }: { method: string, args?: any[], errorMessage: string }) => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Internal Server Error'
      })

      await expect(
        (credentialsService as any)[method](...args)
      ).rejects.toThrow(errorMessage)
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(
        credentialsService.getAllCredentials()
      ).rejects.toThrow('Network error')
    })

    it('should handle malformed JSON responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON')
        }
      })

      await expect(
        credentialsService.getAllCredentials()
      ).rejects.toThrow('Invalid JSON')
    })
  })

  describe('Credential Validation', () => {
    it('should handle encrypted credentials properly', async () => {
      const mockResponse = {
        credentials: {
          SECRET_KEY: {
            encrypted_value: 'encrypted_abc123',
            is_encrypted: true,
            description: 'Encrypted secret'
          }
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const credentials = await credentialsService.getCredentialsByCategory('secrets')

      expect(credentials[0]).toMatchObject({
        key: 'SECRET_KEY',
        value: undefined,
        encrypted_value: 'encrypted_abc123',
        is_encrypted: true
      })
    })

    it('should handle empty credential responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ credentials: {} })
      })

      const credentials = await credentialsService.getCredentialsByCategory('empty_category')

      expect(credentials).toEqual([])
    })

    it('should handle non-object credential values', async () => {
      const mockResponse = {
        credentials: {
          SIMPLE_VALUE: 'just-a-string',
          BOOLEAN_VALUE: true,
          NUMBER_VALUE: 42
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const credentials = await credentialsService.getCredentialsByCategory('mixed')

      expect(credentials).toHaveLength(3)
      expect(credentials[0]).toMatchObject({
        key: 'SIMPLE_VALUE',
        value: 'just-a-string',
        is_encrypted: false
      })
    })
  })
})