import React from 'react'
import { vi } from 'vitest'

export const KnowledgeTable = vi.fn(({ items, isLoading, onDelete, onTest }) => (
  <div data-testid="knowledge-table">
    {isLoading && <div>Loading...</div>}
    {items.map((item: any) => (
      <div key={item.id} data-testid={`knowledge-item-${item.id}`}>
        <span>{item.title}</span>
        <button onClick={() => onDelete?.(item.id)}>Delete</button>
        <button onClick={() => onTest?.(item.id)}>Test</button>
      </div>
    ))}
  </div>
))