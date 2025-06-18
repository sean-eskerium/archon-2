import { rest } from 'msw'
import { mockApiResponses } from './mockData'

export const handlers = [
  // Projects
  rest.get('/api/projects', (req, res, ctx) => {
    return res(ctx.json(mockApiResponses.projects.list))
  }),
  
  rest.post('/api/projects', (req, res, ctx) => {
    return res(ctx.status(201), ctx.json(mockApiResponses.projects.create))
  }),
  
  rest.put('/api/projects/:id', (req, res, ctx) => {
    return res(ctx.json(mockApiResponses.projects.update))
  }),
  
  rest.delete('/api/projects/:id', (req, res, ctx) => {
    return res(ctx.status(204))
  }),
  
  // Tasks
  rest.get('/api/projects/:projectId/tasks', (req, res, ctx) => {
    return res(ctx.json(mockApiResponses.tasks.list))
  }),
  
  rest.post('/api/projects/:projectId/tasks', (req, res, ctx) => {
    return res(ctx.status(201), ctx.json(mockApiResponses.tasks.create))
  }),
  
  // Settings
  rest.get('/api/settings', (req, res, ctx) => {
    return res(ctx.json({
      api_keys: { openai: 'sk-****' },
      features: { projects: true, mcp: true }
    }))
  }),
  
  rest.put('/api/settings', (req, res, ctx) => {
    return res(ctx.json({ success: true }))
  })
]