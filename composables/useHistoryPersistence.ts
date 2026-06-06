/**
 * History Persistence Composable
 * Manages persistent storage and retrieval of clustering run history using Redis backend
 */

import { ref, computed, nextTick } from 'vue'
import type { ClusterRun } from './useGlobalState'

export interface HistoryPersistenceState {
  isLoading: boolean
  isConnected: boolean
  lastSyncTime: Date | null
  syncEnabled: boolean
  autoSyncInterval: number
  error: string | null
}

export interface HistoryStats {
  totalRuns: number
  recentRuns: number
  algorithms: Record<string, number>
  datasets: Record<string, number>
  avgClusterCount: number
}

export interface PaginatedRuns {
  runs: ClusterRun[]
  total: number
  page: number
  limit: number
  hasMore: boolean
}

export interface ImportResult {
  success: boolean
  imported: number
  total: number
  errors: string[]
}

export interface OperationResult {
  success: boolean
  message: string
}

export function useHistoryPersistence() {
  // State
  const state = ref<HistoryPersistenceState>({
    isLoading: false,
    isConnected: false,
    lastSyncTime: null,
    syncEnabled: false, // Will be set during initialization
    autoSyncInterval: 30000, // 30 seconds
    error: null
  })

  // Data normalization utility
  const normalizeRunData = (run: any): ClusterRun => {
    return {
      ...run,
      // Ensure timestamp is a Date object
      timestamp: typeof run.timestamp === 'string' ? new Date(run.timestamp) : run.timestamp,
      // Ensure numerical fields are numbers
      selectedK: typeof run.selectedK === 'string' ? parseInt(run.selectedK, 10) : run.selectedK,
      selectedPower: typeof run.selectedPower === 'string' ? parseFloat(run.selectedPower) : run.selectedPower,
      actualClusterCount: typeof run.actualClusterCount === 'string' ? parseInt(run.actualClusterCount, 10) : run.actualClusterCount,
      // Ensure metrics are numbers if they exist
      metrics: run.metrics ? {
        ...run.metrics,
        silhouetteScore: typeof run.metrics.silhouetteScore === 'string' ? parseFloat(run.metrics.silhouetteScore) : run.metrics.silhouetteScore,
        dbIndex: typeof run.metrics.dbIndex === 'string' ? parseFloat(run.metrics.dbIndex) : run.metrics.dbIndex,
        calinskiHarabasz: typeof run.metrics.calinskiHarabasz === 'string' ? parseFloat(run.metrics.calinskiHarabasz) : run.metrics.calinskiHarabasz,
        ari: typeof run.metrics.ari === 'string' ? parseFloat(run.metrics.ari) : run.metrics.ari,
        discoScore: typeof run.metrics.discoScore === 'string' ? parseFloat(run.metrics.discoScore) : run.metrics.discoScore,
      } : run.metrics
    }
  }

  // Auto-sync interval
  let autoSyncTimer: NodeJS.Timeout | null = null

  // API helpers
  const apiRequest = async <T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> => {
    state.value.error = null
    
    try {
      const response = await $fetch<T>(endpoint, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      })
      
      state.value.isConnected = true
      return response
    } catch (error: any) {
      state.value.isConnected = false
      state.value.error = error.message || 'API request failed'
      console.error(`History API Error [${endpoint}]:`, error)
      throw error
    }
  }

  // Core API functions
  const saveRun = async (run: ClusterRun): Promise<boolean> => {
    // Skip if sync is disabled
    if (!state.value.syncEnabled) {
      return true
    }
    
    try {
      state.value.isLoading = true
      
      // Convert run to API format
      const apiRun = {
        id: run.id,
        timestamp: run.timestamp,
        dataset: run.dataset,
        treeType: run.treeType,
        partitionMethod: run.partitionMethod,
        selectedK: run.selectedK,
        selectedPower: run.selectedPower,
        actualClusterCount: run.actualClusterCount,
        parameters: run.parameters,
        metrics: run.metrics,
        clusterData: run.clusterData,
        treeData: run.treeData
      }
      
      await apiRequest('/api/history/runs', {
        method: 'POST',
        body: JSON.stringify(apiRun)
      })
      
      state.value.lastSyncTime = new Date()
      return true
    } catch (error) {
      console.warn('Failed to save run to history (will continue without Redis):', error)
      // Disable sync if server is unavailable
      state.value.syncEnabled = false
      return false
    } finally {
      state.value.isLoading = false
    }
  }

  const getRun = async (runId: string): Promise<ClusterRun | null> => {
    // Skip if sync is disabled
    if (!state.value.syncEnabled) {
      return null
    }
    
    try {
      state.value.isLoading = true
      
      const response = await apiRequest<ClusterRun>(`/api/history/runs/${runId}`)
      
      // Normalize the run data
      return normalizeRunData(response)
    } catch (error) {
      console.warn('Failed to get run from history (will continue without Redis):', error)
      // Disable sync if server is unavailable
      state.value.syncEnabled = false
      return null
    } finally {
      state.value.isLoading = false
    }
  }

  const listRuns = async (
    page: number = 1,
    limit: number = 50
  ): Promise<PaginatedRuns> => {
    // Skip if sync is disabled
    if (!state.value.syncEnabled) {
      return {
        runs: [],
        total: 0,
        page,
        limit,
        hasMore: false
      }
    }
    
    try {
      state.value.isLoading = true
      
      const response = await apiRequest<PaginatedRuns>(
        `/api/history/runs?page=${page}&limit=${limit}`
      )
      
      // Normalize all run data
      response.runs = response.runs.map(run => normalizeRunData(run))
      
      return response
    } catch (error) {
      console.warn('Failed to list runs from history (will continue without Redis):', error)
      // Disable sync if server is unavailable
      state.value.syncEnabled = false
      return {
        runs: [],
        total: 0,
        page,
        limit,
        hasMore: false
      }
    } finally {
      state.value.isLoading = false
    }
  }

  const deleteRun = async (runId: string): Promise<boolean> => {
    try {
      state.value.isLoading = true
      
      await apiRequest<OperationResult>(`/api/history/runs/${runId}`, {
        method: 'DELETE'
      })
      
      return true
    } catch (error) {
      console.error('Failed to delete run from history:', error)
      return false
    } finally {
      state.value.isLoading = false
    }
  }



  const getStats = async (): Promise<HistoryStats | null> => {
    try {
      const response = await apiRequest<HistoryStats>('/api/history/stats')
      return response
    } catch (error) {
      console.error('Failed to get history stats:', error)
      return null
    }
  }

  const checkHealth = async (): Promise<boolean> => {
    try {
      const response = await apiRequest<any>('/api/history/health')
      state.value.isConnected = response.status === 'healthy'
      return state.value.isConnected
    } catch (error) {
      state.value.isConnected = false
      return false
    }
  }

  // Sync management
  const startAutoSync = () => {
    if (autoSyncTimer) {
      clearInterval(autoSyncTimer)
    }
    
    if (state.value.syncEnabled && state.value.autoSyncInterval > 0) {
      autoSyncTimer = setInterval(async () => {
        await checkHealth()
      }, state.value.autoSyncInterval)
    }
  }

  const stopAutoSync = () => {
    if (autoSyncTimer) {
      clearInterval(autoSyncTimer)
      autoSyncTimer = null
    }
  }

  const setSyncEnabled = (enabled: boolean) => {
    state.value.syncEnabled = enabled
    if (enabled) {
      startAutoSync()
    } else {
      stopAutoSync()
    }
  }

  const setSyncInterval = (interval: number) => {
    state.value.autoSyncInterval = interval
    if (state.value.syncEnabled) {
      startAutoSync()
    }
  }

  // Batch operations
  const syncRuns = async (runs: ClusterRun[]): Promise<{ success: number; failed: number }> => {
    let success = 0
    let failed = 0
    
    state.value.isLoading = true
    
    try {
      // Process runs in batches to avoid overwhelming the server
      const batchSize = 10
      for (let i = 0; i < runs.length; i += batchSize) {
        const batch = runs.slice(i, i + batchSize)
        
        const promises = batch.map(async (run) => {
          try {
            await saveRun(run)
            success++
          } catch (error) {
            console.error(`Failed to sync run ${run.id}:`, error)
            failed++
          }
        })
        
        await Promise.all(promises)
        
        // Brief pause between batches
        if (i + batchSize < runs.length) {
          await new Promise(resolve => setTimeout(resolve, 100))
        }
      }
    } finally {
      state.value.isLoading = false
    }
    
    return { success, failed }
  }

  // Computed properties
  const isReady = computed(() => state.value.isConnected && !state.value.isLoading)
  const hasError = computed(() => state.value.error !== null)
  const statusText = computed(() => {
    if (state.value.isLoading) return 'Loading...'
    if (!state.value.isConnected) return 'Disconnected'
    if (state.value.error) return `Error: ${state.value.error}`
    return 'Connected'
  })

  // Initialize
  const initialize = async () => {
    try {
      // Get runtime config safely
      let historyPersistenceEnabled = false
      try {
        const config = useRuntimeConfig()
        historyPersistenceEnabled = config.public.historyPersistenceEnabled
      } catch (error) {
        console.warn('Could not access runtime config, disabling history persistence:', error)
      }
      
      // Set initial sync state from config
      state.value.syncEnabled = historyPersistenceEnabled
      
      if (historyPersistenceEnabled) {
        const isHealthy = await checkHealth()
        if (isHealthy) {
          startAutoSync()
        } else {
          // Disable sync if Redis is not available
          state.value.syncEnabled = false
        }
      }
    } catch (error) {
      console.warn('Failed to initialize history persistence, disabling Redis sync:', error)
      state.value.syncEnabled = false
    }
  }

  // Cleanup
  const cleanup = () => {
    stopAutoSync()
  }

  return {
    // State
    state: readonly(state),
    
    // Computed
    isReady,
    hasError,
    statusText,
    
    // Core API
    saveRun,
    getRun,
    listRuns,
    deleteRun,
    getStats,
    checkHealth,
    
    // Sync management
    setSyncEnabled,
    setSyncInterval,
    syncRuns,
    
    // Lifecycle
    initialize,
    cleanup
  }
}