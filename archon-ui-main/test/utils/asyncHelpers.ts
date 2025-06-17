import { waitFor } from '@testing-library/react'

export const waitForCondition = async (
  condition: () => boolean,
  options = { timeout: 5000, interval: 50 }
) => {
  const { timeout, interval } = options
  const startTime = Date.now()
  
  while (!condition()) {
    if (Date.now() - startTime > timeout) {
      throw new Error('Condition not met within timeout')
    }
    await new Promise(resolve => setTimeout(resolve, interval))
  }
}

export const retryAsync = async <T>(
  fn: () => Promise<T>,
  retries = 3,
  delay = 100
): Promise<T> => {
  try {
    return await fn()
  } catch (error) {
    if (retries === 0) throw error
    await new Promise(resolve => setTimeout(resolve, delay))
    return retryAsync(fn, retries - 1, delay * 2)
  }
}

export const timeoutPromise = <T>(
  promise: Promise<T>,
  timeout: number,
  message = 'Promise timed out'
): Promise<T> => {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(message)), timeout)
    )
  ])
}

export const flushPromises = () => 
  new Promise(resolve => setImmediate(resolve))

export const waitForDebounce = (ms = 300) =>
  new Promise(resolve => setTimeout(resolve, ms))