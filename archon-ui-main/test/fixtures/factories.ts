import { faker } from '@faker-js/faker'

export const createMockProject = (overrides = {}) => ({
  id: faker.string.uuid(),
  title: faker.lorem.words(3),
  description: faker.lorem.paragraph(),
  status: 'active',
  created_at: faker.date.past().toISOString(),
  updated_at: faker.date.recent().toISOString(),
  ...overrides
})

export const createMockTask = (overrides = {}) => ({
  id: faker.string.uuid(),
  title: faker.lorem.sentence(),
  description: faker.lorem.paragraph(),
  status: faker.helpers.arrayElement(['todo', 'in_progress', 'done']),
  assignee: faker.helpers.arrayElement(['User', 'Archon', 'AI IDE Agent']),
  project_id: faker.string.uuid(),
  created_at: faker.date.past().toISOString(),
  ...overrides
})

export const createMockUser = (overrides = {}) => ({
  id: faker.string.uuid(),
  name: faker.person.fullName(),
  email: faker.internet.email(),
  avatar: faker.image.avatar(),
  ...overrides
})

export const createMockDocument = (overrides = {}) => ({
  id: faker.string.uuid(),
  title: faker.lorem.words(4),
  content: faker.lorem.paragraphs(3),
  source: faker.internet.url(),
  created_at: faker.date.past().toISOString(),
  ...overrides
})