import { describe, it, expect } from 'vitest'
import * as lucideReact from 'lucide-react'

describe('Setup verification', () => {
  it('should have lucide-react mocked', () => {
    expect(lucideReact).toBeDefined()
    expect(lucideReact.Eye).toBeDefined()
    expect(lucideReact.RefreshCw).toBeDefined()
    expect(lucideReact.Network).toBeDefined()
  })
})