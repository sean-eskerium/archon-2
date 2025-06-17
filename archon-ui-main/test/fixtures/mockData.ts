// Static test data
export const mockProjects = [
  {
    id: '1',
    title: 'Test Project 1',
    description: 'Description for test project 1',
    status: 'active',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z'
  },
  {
    id: '2',
    title: 'Test Project 2',
    description: 'Description for test project 2',
    status: 'archived',
    created_at: '2024-01-03T00:00:00Z',
    updated_at: '2024-01-04T00:00:00Z'
  }
]

export const mockTasks = [
  {
    id: '1',
    title: 'Test Task 1',
    description: 'Task description',
    status: 'todo',
    assignee: 'User',
    project_id: '1'
  },
  {
    id: '2',
    title: 'Test Task 2',
    description: 'Another task',
    status: 'in_progress',
    assignee: 'Archon',
    project_id: '1'
  }
]

export const mockApiResponses = {
  projects: {
    list: { data: mockProjects, total: 2 },
    create: { data: mockProjects[0] },
    update: { data: { ...mockProjects[0], title: 'Updated Title' } },
    delete: { success: true }
  },
  tasks: {
    list: { data: mockTasks, total: 2 },
    create: { data: mockTasks[0] },
    update: { data: { ...mockTasks[0], status: 'done' } },
    delete: { success: true }
  }
}