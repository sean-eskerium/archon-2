import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest'
import { projectCreationProgressService } from '@/services/projectCreationProgressService'
import { MockWebSocket } from '../setup'
import type { ProjectCreationProgressData } from '@/services/projectCreationProgressService'

// Mock environment
(import.meta as any).env = { VITE_API_BASE_URL: 'http://localhost:8080' }

describe('projectCreationProgressService', () => {
  const wsUrl = 'ws://localhost:8080'
  let consoleLog: ReturnType<typeof vi.spyOn>
  let consoleWarn: ReturnType<typeof vi.spyOn>
  let consoleError: ReturnType<typeof vi.spyOn>
  
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock console methods
    consoleLog = vi.spyOn(console, 'log').mockImplementation()
    consoleWarn = vi.spyOn(console, 'warn').mockImplementation()
    consoleError = vi.spyOn(console, 'error').mockImplementation()
    // Clear any existing connections
    projectCreationProgressService.disconnect()
    projectCreationProgressService.isReconnecting = false
  })

  afterEach(() => {
    vi.restoreAllMocks()
    projectCreationProgressService.disconnect()
    consoleLog.mockRestore()
    consoleWarn.mockRestore()
    consoleError.mockRestore()
  })

  describe('Progress Streaming', () => {
    it('should stream project creation progress', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      expect(ws).toBeInstanceOf(MockWebSocket)
      expect(ws.url).toBe(`${wsUrl}/api/project-creation-progress/${progressId}`)
    })

    it('should handle creation step updates', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      // Simulate connection open
      ws.onopen?.(new Event('open'))
      expect(consoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Connected to project creation progress stream')
      )

      // Test different creation steps
      const stepUpdates: ProjectCreationProgressData[] = [
        {
          progressId,
          status: 'starting',
          percentage: 0,
          currentStep: 'Initializing project creation',
          logs: ['Starting project creation...']
        },
        {
          progressId,
          status: 'initializing_agents',
          percentage: 15,
          currentStep: 'Setting up AI agents',
          logs: ['Initializing document agent', 'Initializing requirements agent']
        },
        {
          progressId,
          status: 'processing_requirements',
          percentage: 30,
          currentStep: 'Processing requirements',
          eta: '2 minutes',
          logs: ['Analyzing project requirements', 'Extracting key features']
        },
        {
          progressId,
          status: 'ai_generation',
          percentage: 60,
          currentStep: 'AI generating documentation',
          logs: ['Generating README.md', 'Creating API documentation']
        },
        {
          progressId,
          status: 'finalizing_docs',
          percentage: 85,
          currentStep: 'Finalizing documents',
          logs: ['Formatting documentation', 'Adding code examples']
        },
        {
          progressId,
          status: 'saving_to_database',
          percentage: 95,
          currentStep: 'Saving to database',
          logs: ['Storing project data', 'Creating indexes']
        },
        {
          progressId,
          status: 'completed',
          percentage: 100,
          currentStep: 'Project created successfully',
          duration: '3m 45s',
          project: { id: 'proj-123', title: 'New Project' },
          logs: ['Project creation completed']
        }
      ]

      stepUpdates.forEach((update, index) => {
        ws.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify({
            type: 'project_progress',
            data: update
          })
        }))
        
        expect(onMessage).toHaveBeenNthCalledWith(index + 1, update)
      })

      expect(onMessage).toHaveBeenCalledTimes(stepUpdates.length)
      
      // Verify completed project includes project data
      const lastCall = onMessage.mock.calls[onMessage.mock.calls.length - 1][0]
      expect(lastCall.status).toBe('completed')
      expect(lastCall.project).toBeDefined()
    })

    it('should calculate overall progress percentage', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      // Test progress percentage for each major step
      const expectedPercentages = [
        { status: 'starting', percentage: 0 },
        { status: 'initializing_agents', percentage: 15 },
        { status: 'generating_docs', percentage: 25 },
        { status: 'processing_requirements', percentage: 40 },
        { status: 'ai_generation', percentage: 60 },
        { status: 'finalizing_docs', percentage: 85 },
        { status: 'saving_to_database', percentage: 95 },
        { status: 'completed', percentage: 100 }
      ]

      expectedPercentages.forEach(({ status, percentage }) => {
        const progressData: ProjectCreationProgressData = {
          progressId,
          status: status as any,
          percentage,
          logs: []
        }

        ws.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify({
            type: 'project_progress',
            data: progressData
          })
        }))
      })

      // Verify all percentages are correctly passed
      expectedPercentages.forEach((expected, index) => {
        expect(onMessage).toHaveBeenNthCalledWith(
          index + 1,
          expect.objectContaining({ percentage: expected.percentage })
        )
      })
    })
  })

  describe('Error Handling', () => {
    it('should show error states during creation', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      const errorData: ProjectCreationProgressData = {
        progressId,
        status: 'error',
        percentage: 45,
        error: 'Failed to generate documentation: AI service unavailable',
        currentStep: 'AI generation failed',
        logs: ['Error: Connection to AI service failed', 'Retrying...', 'Max retries exceeded']
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'project_error',
          data: errorData
        })
      }))

      expect(onMessage).toHaveBeenCalledWith(errorData)
      expect(onMessage.mock.calls[0][0].error).toContain('AI service unavailable')
    })

    it('should validate progress data format', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      // Test invalid messages
      const invalidMessages = [
        { type: 'project_progress' }, // No data
        { type: 'project_progress', data: null }, // Null data
        { type: 'unknown_type', data: {} } // Unknown type
      ]

      invalidMessages.forEach(msg => {
        ws.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify(msg)
        }))
      })

      // These should not trigger callback
      expect(onMessage).not.toHaveBeenCalled()

      // Valid message should work
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'project_progress',
          data: {
            progressId,
            status: 'starting',
            percentage: 0,
            logs: []
          }
        })
      }))

      expect(onMessage).toHaveBeenCalledTimes(1)
    })

    it('should handle malformed JSON', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      // Send invalid JSON
      ws.onmessage?.(new MessageEvent('message', {
        data: 'not valid json {}'
      }))

      expect(onMessage).not.toHaveBeenCalled()
      expect(consoleError).toHaveBeenCalledWith(
        'Failed to parse project creation progress message:',
        expect.any(Error)
      )
    })

    it('should handle WebSocket errors', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      const error = new Event('error')
      ws.onerror?.(error)

      expect(consoleError).toHaveBeenCalledWith(
        'Project creation progress WebSocket error:',
        error
      )
    })
  })

  describe('Connection Management', () => {
    it('should handle WebSocket disconnect during creation', async () => {
      vi.useFakeTimers()
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage, {
        autoReconnect: true,
        reconnectDelay: 2000
      })

      // Simulate disconnect
      ws.onclose?.(new CloseEvent('close'))

      expect(projectCreationProgressService.isReconnecting).toBe(true)
      expect(consoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Project creation progress stream disconnected')
      )

      // Fast forward to trigger reconnection
      vi.advanceTimersByTime(2000)
      
      // Should create new connection
      expect(MockWebSocket).toHaveBeenCalledTimes(2)
      
      vi.useRealTimers()
    })

    it('should clean up resources on completion', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      expect(projectCreationProgressService.isConnected()).toBe(false) // MockWebSocket starts as CONNECTING

      // Simulate completion
      const completionData: ProjectCreationProgressData = {
        progressId,
        status: 'completed',
        percentage: 100,
        project: { id: 'proj-123' },
        logs: ['Completed']
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'project_completed',
          data: completionData
        })
      }))

      // Manual cleanup
      projectCreationProgressService.disconnect()
      
      expect(ws.close).toHaveBeenCalled()
      expect(projectCreationProgressService.isConnected()).toBe(false)
    })

    it('should not auto-reconnect when disabled', () => {
      vi.useFakeTimers()
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage, {
        autoReconnect: false
      })

      // Simulate disconnect
      ws.onclose?.(new CloseEvent('close'))

      expect(projectCreationProgressService.isReconnecting).toBe(false)
      
      // Should not attempt reconnection
      vi.advanceTimersByTime(10000)
      expect(MockWebSocket).toHaveBeenCalledTimes(1)
      
      vi.useRealTimers()
    })

    it('should track connection state accurately', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      expect(projectCreationProgressService.isConnected()).toBe(false)
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      // MockWebSocket starts as CONNECTING
      expect(projectCreationProgressService.isConnected()).toBe(false)
      
      // Simulate open connection
      (ws as any).readyState = MockWebSocket.OPEN
      expect(projectCreationProgressService.isConnected()).toBe(true)
      
      // Disconnect
      projectCreationProgressService.disconnect()
      expect(projectCreationProgressService.isConnected()).toBe(false)
    })
  })

  describe('Special Cases', () => {
    it('should handle creation timeout', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      // Simulate timeout error
      const timeoutData: ProjectCreationProgressData = {
        progressId,
        status: 'error',
        percentage: 60,
        error: 'Project creation timeout: Maximum time exceeded (10 minutes)',
        currentStep: 'AI generation timed out',
        logs: ['Processing took too long', 'Operation cancelled']
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'project_error',
          data: timeoutData
        })
      }))

      expect(onMessage).toHaveBeenCalledWith(timeoutData)
      expect(onMessage.mock.calls[0][0].error).toContain('timeout')
    })

    it('should ignore ping messages', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      // Send ping message
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({ type: 'ping' })
      }))

      expect(onMessage).not.toHaveBeenCalled()
    })

    it('should handle ETA updates', () => {
      const progressId = 'project-create-123'
      const onMessage = vi.fn()
      
      const ws = projectCreationProgressService.streamProgress(progressId, onMessage)
      
      const progressWithETA: ProjectCreationProgressData = {
        progressId,
        status: 'ai_generation',
        percentage: 45,
        eta: '3 minutes remaining',
        currentStep: 'Generating technical documentation',
        logs: ['Processing section 2 of 5']
      }

      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'project_progress',
          data: progressWithETA
        })
      }))

      expect(onMessage).toHaveBeenCalledWith(progressWithETA)
      expect(onMessage.mock.calls[0][0].eta).toBe('3 minutes remaining')
    })
  })

  describe('Backward Compatibility', () => {
    test.each([
      { method: 'connect', args: ['progress-123'] },
      { method: 'onProgress', args: [vi.fn()] },
      { method: 'onCompleted', args: [vi.fn()] },
      { method: 'onError', args: [vi.fn()] }
    ])('should warn about deprecated $method', ({ method, args }: { method: string, args: any[] }) => {
      (projectCreationProgressService as any)[method](...args)
      
      expect(consoleWarn).toHaveBeenCalledWith(
        expect.stringContaining(`${method}() is deprecated`)
      )
    })
  })
})