import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { projectService } from '@/services/projectService'

// Mocks are already set up in setup.ts

describe('projectService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked((globalThis as any).fetch).mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Project Operations', () => {
    it('should create project successfully', async () => {
      const createRequest = {
        title: 'New Project',
        description: 'New project description',
        icon: '🚀',
        color: 'green',
        pinned: false
      }

      const mockResponse = { 
        id: 'new-project-123',
        ...createRequest,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }
      
      vi.mocked((globalThis as any).fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      } as Response)

      const result = await projectService.createProject(createRequest as any)

      expect((globalThis as any).fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/projects'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
      )

      expect(result).toMatchObject({
        id: 'new-project-123',
        title: 'New Project',
        progress: 0
      })
    })

    it('should list projects', async () => {
      const mockProjects = [
        { id: 'project-1', title: 'Project 1', pinned: false },
        { id: 'project-2', title: 'Project 2', pinned: true }
      ]
      
      vi.mocked((globalThis as any).fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockProjects
      } as Response)

      const result = await projectService.listProjects()

      expect((globalThis as any).fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/projects'),
        expect.any(Object)
      )

      expect(result).toHaveLength(2)
      expect(result[0]).toHaveProperty('pinned', false)
      expect(result[1]).toHaveProperty('pinned', true)
    })

    it('should update project', async () => {
      const updates = { title: 'Updated Title', pinned: true }
      const mockUpdatedProject = { 
        id: 'project-123',
        ...updates,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }
      
      vi.mocked((globalThis as any).fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdatedProject
      } as Response)

      const result = await projectService.updateProject('project-123', updates as any)

      expect((globalThis as any).fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/projects/project-123'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(updates)
        })
      )

      expect(result.title).toBe('Updated Title')
      expect(result.pinned).toBe(true)
    })

    it('should delete project', async () => {
      vi.mocked((globalThis as any).fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      } as Response)

      await projectService.deleteProject('project-123')

      expect((globalThis as any).fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/projects/project-123'),
        expect.objectContaining({ method: 'DELETE' })
      )
    })
  })

  describe('Error Handling', () => {
    it('should handle 404 errors', async () => {
      vi.mocked((globalThis as any).fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ error: 'Project not found' })
      } as Response)

      await expect(projectService.getProject('non-existent')).rejects.toThrow()
    })

    it('should handle network errors', async () => {
      vi.mocked((globalThis as any).fetch).mockRejectedValueOnce(new Error('Network error'))

      await expect(projectService.listProjects()).rejects.toThrow('Network error')
    })
  })

  describe('Task Operations', () => {
    it('should create task', async () => {
      const createRequest = {
        project_id: 'project-123',
        title: 'New Task',
        description: 'Task description',
        priority: 'high',
        assignee: 'User'
      }

      const mockTask = { 
        id: 'task-123',
        ...createRequest,
        status: 'todo',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }

      vi.mocked((globalThis as any).fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTask
      } as Response)

      const result = await projectService.createTask(createRequest as any)

      expect((globalThis as any).fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/tasks'),
        expect.objectContaining({
          method: 'POST'
        })
      )

      expect(result).toHaveProperty('id', 'task-123')
      expect(result).toHaveProperty('uiStatus')
    })

    it('should update task status', async () => {
      const updatedTask = {
        id: 'task-123',
        status: 'doing',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }
      
      vi.mocked((globalThis as any).fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => updatedTask
      } as Response)

      const result = await projectService.updateTaskStatus('task-123', 'doing')

      expect((globalThis as any).fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/tasks/task-123?status=doing'),
        expect.objectContaining({ method: 'PUT' })
      )

      expect(result.status).toBe('doing')
    })
  })

  describe('WebSocket Integration', () => {
    it('should initialize WebSocket on subscription', () => {
      const unsubscribe = projectService.subscribeToProjectUpdates('project-123', vi.fn())

      expect((globalThis as any).WebSocket).toHaveBeenCalledWith(
        expect.stringContaining('ws://localhost:8080/ws/project-updates')
      )

      unsubscribe()
    })
  })
})