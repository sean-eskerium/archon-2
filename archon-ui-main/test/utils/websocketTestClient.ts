import { vi } from 'vitest'

export class WebSocketTestClient {
  private callbacks: Map<string, Set<Function>> = new Map()
  private messageQueue: any[] = []
  private connected = false

  connect() {
    this.connected = true
    return Promise.resolve()
  }

  disconnect() {
    this.connected = false
    this.callbacks.clear()
    this.messageQueue = []
  }

  subscribe(channel: string, callback: Function) {
    if (!this.callbacks.has(channel)) {
      this.callbacks.set(channel, new Set())
    }
    this.callbacks.get(channel)!.add(callback)
    
    // Return unsubscribe function
    return () => {
      this.callbacks.get(channel)?.delete(callback)
    }
  }

  send(message: any) {
    if (this.connected) {
      this.messageQueue.push(message)
    } else {
      throw new Error('WebSocket not connected')
    }
  }

  // Test helper methods
  simulateMessage(channel: string, message: any) {
    const callbacks = this.callbacks.get(channel) || new Set()
    callbacks.forEach(cb => cb(message))
  }

  simulateDisconnect() {
    this.connected = false
  }

  simulateReconnect() {
    this.connected = true
  }

  getMessageQueue() {
    return [...this.messageQueue]
  }

  clearMessageQueue() {
    this.messageQueue = []
  }

  isConnected() {
    return this.connected
  }

  getSubscriptionCount(channel: string) {
    return this.callbacks.get(channel)?.size || 0
  }
}