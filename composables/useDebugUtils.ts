/**
 * Debug Utilities Composable
 * 
 * Provides safe logging utilities that automatically disable in production
 * to prevent memory leaks from console.log statements.
 */

export const useDebugUtils = () => {
  const isDevelopment = process.env.NODE_ENV === 'development'
  
  // Safe logging functions that only work in development
  const debug = isDevelopment ? console.log : () => {}
  const debugWarn = isDevelopment ? console.warn : () => {}
  const debugError = isDevelopment ? console.error : () => {}
  const debugInfo = isDevelopment ? console.info : () => {}
  const debugTable = isDevelopment ? console.table : () => {}
  const debugGroup = isDevelopment ? console.group : () => {}
  const debugGroupEnd = isDevelopment ? console.groupEnd : () => {}
  const debugTime = isDevelopment ? console.time : () => {}
  const debugTimeEnd = isDevelopment ? console.timeEnd : () => {}
  
  /**
   * Performance timing utility
   */
  const performanceTimer = (label: string) => {
    let startTime: number
    
    return {
      start: () => {
        startTime = performance.now()
        debugTime(label)
      },
      end: () => {
        const endTime = performance.now()
        debugTimeEnd(label)
        const duration = endTime - startTime
        if (isDevelopment) {
          debug(`${label} took ${duration.toFixed(2)}ms`)
        }
        return duration
      }
    }
  }
  
  /**
   * Memory usage logger for specific operations
   */
  const logMemoryUsage = (label: string) => {
    if (!isDevelopment) return
    
    if (typeof window !== 'undefined' && (performance as any).memory) {
      const memory = (performance as any).memory
      debug(`[${label}] Memory usage:`, {
        used: `${Math.round(memory.usedJSHeapSize / 1024 / 1024)}MB`,
        total: `${Math.round(memory.totalJSHeapSize / 1024 / 1024)}MB`,
        limit: `${Math.round(memory.jsHeapSizeLimit / 1024 / 1024)}MB`
      })
    }
  }
  
  /**
   * Object size estimation for debugging
   */
  const logObjectSize = (obj: any, label: string) => {
    if (!isDevelopment) return
    
    const getObjectSize = (obj: any): number => {
      let size = 0
      
      if (obj === null || obj === undefined) return 0
      
      switch (typeof obj) {
        case 'boolean':
          return 4
        case 'number':
          return 8
        case 'string':
          return obj.length * 2
        case 'object':
          if (Array.isArray(obj)) {
            size += obj.length * 8 // Array overhead
            for (const item of obj) {
              size += getObjectSize(item)
            }
          } else {
            for (const key in obj) {
              if (obj.hasOwnProperty(key)) {
                size += key.length * 2 // Key size
                size += getObjectSize(obj[key])
              }
            }
          }
          break
      }
      
      return size
    }
    
    const sizeBytes = getObjectSize(obj)
    const sizeMB = sizeBytes / (1024 * 1024)
    
    debug(`[${label}] Object size: ${sizeBytes} bytes (${sizeMB.toFixed(2)}MB)`)
  }
  
  /**
   * Safe JSON stringification for debugging
   */
  const safeStringify = (obj: any, maxDepth: number = 3): string => {
    const seen = new WeakSet()
    
    const replacer = (key: string, value: any, depth: number = 0): any => {
      if (depth > maxDepth) return '[Max Depth Reached]'
      if (value === null) return null
      if (typeof value !== 'object') return value
      if (seen.has(value)) return '[Circular Reference]'
      
      seen.add(value)
      
      if (Array.isArray(value)) {
        return value.length > 10 
          ? `[Array(${value.length})] ${value.slice(0, 3).map(v => replacer('', v, depth + 1))}`
          : value.map(v => replacer('', v, depth + 1))
      }
      
      const keys = Object.keys(value)
      if (keys.length > 10) {
        const sample = keys.slice(0, 3).reduce((acc, k) => {
          acc[k] = replacer(k, value[k], depth + 1)
          return acc
        }, {} as any)
        return { ...sample, '...': `${keys.length - 3} more keys` }
      }
      
      return keys.reduce((acc, k) => {
        acc[k] = replacer(k, value[k], depth + 1)
        return acc
      }, {} as any)
    }
    
    try {
      return JSON.stringify(obj, (key, value) => replacer(key, value), 2)
    } catch (error) {
      return `[Stringify Error: ${error}]`
    }
  }
  
  /**
   * Development-only assertions
   */
  const assert = (condition: boolean, message: string) => {
    if (isDevelopment && !condition) {
      debugError(`Assertion failed: ${message}`)
      throw new Error(`Assertion failed: ${message}`)
    }
  }
  
  /**
   * Conditional debugging based on environment flags
   */
  const debugIf = (condition: boolean) => ({
    log: condition && isDevelopment ? console.log : () => {},
    warn: condition && isDevelopment ? console.warn : () => {},
    error: condition && isDevelopment ? console.error : () => {},
    info: condition && isDevelopment ? console.info : () => {}
  })
  
  return {
    // Basic logging
    debug,
    debugWarn,
    debugError,
    debugInfo,
    debugTable,
    debugGroup,
    debugGroupEnd,
    debugTime,
    debugTimeEnd,
    
    // Advanced utilities
    performanceTimer,
    logMemoryUsage,
    logObjectSize,
    safeStringify,
    assert,
    debugIf,
    
    // Environment info
    isDevelopment,
    isProduction: !isDevelopment
  }
}