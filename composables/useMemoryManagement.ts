/**
 * Memory Management Composable
 * 
 * Provides utilities for monitoring and managing memory usage in the frontend
 * to prevent excessive RAM consumption (like the 10GB issue).
 */

import { ref, onUnmounted, nextTick, getCurrentInstance } from 'vue'

interface MemoryInfo {
  usedJSHeapSize: number
  totalJSHeapSize: number
  jsHeapSizeLimit: number
}

export const useMemoryManagement = () => {
  const memoryUsage = ref<MemoryInfo | null>(null)
  const memoryWarningThreshold = 200 * 1024 * 1024 // 200MB warning threshold (more aggressive)
  const memoryDangerThreshold = 500 * 1024 * 1024 // 500MB danger threshold (more aggressive)
  
  // Track large objects for cleanup
  const largeObjects = new Set<WeakRef<any>>()
  const componentMemoryMap = new Map<string, number>()
  const d3ElementRefs = new Set<WeakRef<any>>()
  
  /**
   * Monitor current memory usage
   */
  const checkMemoryUsage = (): MemoryInfo | null => {
    if (typeof window !== 'undefined' && (performance as any).memory) {
      const memory = (performance as any).memory as MemoryInfo
      const newMemoryInfo = {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit
      }
      
      // Only update reactive ref if values actually changed to prevent recursive updates
      const current = memoryUsage.value
      if (!current || 
          current.usedJSHeapSize !== newMemoryInfo.usedJSHeapSize ||
          current.totalJSHeapSize !== newMemoryInfo.totalJSHeapSize ||
          current.jsHeapSizeLimit !== newMemoryInfo.jsHeapSizeLimit) {
        memoryUsage.value = newMemoryInfo
      }
      
      return newMemoryInfo
    }
    return null
  }
  
  /**
   * Check if memory usage is concerning
   */
  const isMemoryUsageHigh = (): boolean => {
    const memory = checkMemoryUsage()
    if (!memory) return false
    
    return memory.usedJSHeapSize > memoryWarningThreshold
  }
  
  /**
   * Check if memory usage is critical
   */
  const isMemoryUsageCritical = (): boolean => {
    const memory = checkMemoryUsage()
    if (!memory) return false
    
    return memory.usedJSHeapSize > memoryDangerThreshold
  }
  
  /**
   * Format memory size for display
   */
  const formatMemorySize = (bytes: number): string => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    if (bytes === 0) return '0 Bytes'
    
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }
  
  /**
   * Register a large object for tracking
   */
  const trackLargeObject = (obj: any, componentName?: string) => {
    if (obj && typeof obj === 'object') {
      largeObjects.add(new WeakRef(obj))
      
      if (componentName) {
        const size = estimateObjectSize(obj)
        componentMemoryMap.set(componentName, (componentMemoryMap.get(componentName) || 0) + size)
      }
    }
  }
  
  /**
   * Track D3 elements for comprehensive cleanup
   */
  const trackD3Element = (element: any, componentName?: string) => {
    if (element) {
      d3ElementRefs.add(new WeakRef(element))
      if (componentName && process.env.NODE_ENV === 'development') {
        console.log(`[Memory] D3 element tracked for ${componentName}`)
      }
    }
  }
  
  /**
   * Clean up D3 elements
   */
  const cleanupD3Elements = () => {
    let cleaned = 0
    for (const ref of d3ElementRefs) {
      const element = ref.deref()
      if (!element) {
        d3ElementRefs.delete(ref)
        cleaned++
      } else {
        // Force cleanup of D3 element if it exists
        try {
          if (element.selectAll) {
            element.selectAll('*').interrupt().remove()
          }
          if (element.remove) {
            element.remove()
          }
        } catch (e) {
          // Element might be already cleaned up
        }
      }
    }
    return cleaned
  }
  
  /**
   * Get memory usage by component
   */
  const getComponentMemoryUsage = () => {
    return Object.fromEntries(componentMemoryMap)
  }
  
  /**
   * Clear component memory tracking
   */
  const clearComponentMemory = (componentName: string) => {
    componentMemoryMap.delete(componentName)
  }
  
  /**
   * Force garbage collection if available - enhanced with more aggressive cleanup
   */
  const forceGarbageCollection = async () => {
    // Clear tracked objects that are no longer referenced
    let clearedObjects = 0
    for (const ref of largeObjects) {
      if (!ref.deref()) {
        largeObjects.delete(ref)
        clearedObjects++
      }
    }
    
    // Clean up D3 elements
    const clearedD3 = cleanupD3Elements()
    
    // Clear component memory tracking for components that may have been unmounted
    const componentsToClean = []
    for (const [componentName, _] of componentMemoryMap) {
      // Simple heuristic: if component name contains common Vue component patterns
      if (componentName.includes('Scatter') || componentName.includes('Chart') || componentName.includes('Plot')) {
        componentsToClean.push(componentName)
      }
    }
    
    for (const component of componentsToClean) {
      componentMemoryMap.delete(component)
    }
    
    // Force multiple GC cycles for better cleanup
    if (typeof window !== 'undefined' && (window as any).gc) {
      try {
        // Multiple GC passes for more thorough cleanup
        for (let i = 0; i < 3; i++) {
          (window as any).gc()
          await new Promise(resolve => setTimeout(resolve, 10))
        }
        
        if (process.env.NODE_ENV === 'development') {
          console.log(`[Memory] Aggressive GC completed: cleared ${clearedObjects} objects, ${clearedD3} D3 elements, ${componentsToClean.length} component trackers`)
        }
      } catch (e) {
        if (process.env.NODE_ENV === 'development') {
          console.warn('Garbage collection not available')
        }
      }
    }
    
    // Yield to event loop multiple times to allow thorough cleanup
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 50))
    await nextTick()
  }
  
  /**
   * Clear large data structures
   */
  const clearLargeData = (obj: any): any => {
    if (!obj || typeof obj !== 'object') return obj
    
    // If it's an array with many elements, clear it
    if (Array.isArray(obj) && obj.length > 1000) {
      obj.length = 0
      return obj
    }
    
    // If it's an object with large arrays, clear them
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        const value = obj[key]
        if (Array.isArray(value) && value.length > 1000) {
          obj[key] = []
        } else if (value && typeof value === 'object') {
          obj[key] = clearLargeData(value)
        }
      }
    }
    
    return obj
  }
  
  /**
   * Estimate object size in memory
   */
  const estimateObjectSize = (obj: any): number => {
    let size = 0
    
    const calculateSize = (item: any, visited = new Set()): number => {
      if (item === null || item === undefined) return 0
      if (visited.has(item)) return 0
      
      visited.add(item)
      
      switch (typeof item) {
        case 'boolean':
          return 4
        case 'number':
          return 8
        case 'string':
          return item.length * 2
        case 'object':
          if (Array.isArray(item)) {
            let arraySize = 0
            for (const element of item) {
              arraySize += calculateSize(element, visited)
            }
            return arraySize
          } else {
            let objectSize = 0
            for (const key in item) {
              if (item.hasOwnProperty(key)) {
                objectSize += key.length * 2 // key size
                objectSize += calculateSize(item[key], visited)
              }
            }
            return objectSize
          }
        default:
          return 0
      }
    }
    
    return calculateSize(obj)
  }
  
  /**
   * Monitor memory periodically
   */
  let memoryMonitorInterval: NodeJS.Timeout | null = null
  
  const startMemoryMonitoring = (intervalMs: number = 5000) => { // Check every 5 seconds (more frequent)
    // Prevent multiple monitoring intervals
    if (memoryMonitorInterval) {
      console.log('[Memory] Clearing existing memory monitoring interval')
      clearInterval(memoryMonitorInterval)
      memoryMonitorInterval = null
    }
    
    if (process.env.NODE_ENV === 'development') {
      console.log('[Memory] Starting memory monitoring with interval:', intervalMs, 'ms')
    }
    
    memoryMonitorInterval = setInterval(() => {
      const memory = checkMemoryUsage()
      if (memory) {
        // Log memory usage in development
        if (process.env.NODE_ENV === 'development') {
          console.log(`Memory usage: ${formatMemorySize(memory.usedJSHeapSize)}`)
        }
        
        // More aggressive memory management
        if (isMemoryUsageCritical()) { // > 500MB
          console.warn(`⚠️ Critical memory usage: ${formatMemorySize(memory.usedJSHeapSize)}`)
          forceGarbageCollection()
        } else if (isMemoryUsageHigh()) { // > 200MB
          console.warn(`⚡ High memory usage: ${formatMemorySize(memory.usedJSHeapSize)}`)
          // Trigger cleanup for high usage too (more aggressive)
          forceGarbageCollection()
        }
      }
    }, intervalMs)
  }
  
  const stopMemoryMonitoring = () => {
    if (memoryMonitorInterval) {
      if (process.env.NODE_ENV === 'development') {
        console.log('[Memory] Stopping memory monitoring')
      }
      clearInterval(memoryMonitorInterval)
      memoryMonitorInterval = null
    }
  }
  
  // Cleanup on unmount (only if in component context)
  const currentInstance = getCurrentInstance()
  if (currentInstance) {
    onUnmounted(() => {
      stopMemoryMonitoring()
      forceGarbageCollection()
    })
  }
  
  return {
    memoryUsage,
    checkMemoryUsage,
    isMemoryUsageHigh,
    isMemoryUsageCritical,
    formatMemorySize,
    trackLargeObject,
    trackD3Element,
    cleanupD3Elements,
    getComponentMemoryUsage,
    clearComponentMemory,
    forceGarbageCollection,
    clearLargeData,
    estimateObjectSize,
    startMemoryMonitoring,
    stopMemoryMonitoring
  }
} 