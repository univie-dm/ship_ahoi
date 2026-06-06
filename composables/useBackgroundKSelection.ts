// Background K-Selection operation manager
// Manages k-selection polling at module scope so it survives page navigation.
// When the user navigates away from k-selection, polling continues and results
// are stored here for retrieval when they navigate back.

import { ref, readonly } from 'vue'

export interface KSelectionResults {
  k_values: number[]
  metrics: {
    wcss: (number | null)[]
    silhouette: (number | null)[]
    davies_bouldin: (number | null)[]
    calinski_harabasz: (number | null)[]
    elbow_scores: (number | null)[]
    disco: (number | null)[]
  }
  optimal_k_suggestions: Record<string, number>
  cluster_results: Array<{
    k: number
    labels: number[]
    n_clusters: number
  }>
  data_points: number[][]
  high_dimensional_dataset?: boolean
  original_feature_count?: number
  show_only_dr_methods?: boolean
  pca_components?: number[][] | null
  data_cache_id?: string | null
  dr_cluster_id?: string | null
  dr_status?: 'started' | 'failed' | null
  umap_components?: number[][] | null
  tsne_components?: number[][] | null
}

// Module-level singleton state - survives component unmount/remount
const operationId = ref<string | null>(null)
const isRunning = ref(false)
const completedResults = ref<KSelectionResults | null>(null)
const error = ref<string | null>(null)

// Track whether polling is actively happening (the async loop is running)
let pollingPromise: Promise<void> | null = null

// Callback for when results arrive while component is mounted
let onCompleteCallback: ((results: KSelectionResults) => void) | null = null
let onErrorCallback: ((error: string) => void) | null = null

const pollForCompletion = async (opId: string): Promise<KSelectionResults | null> => {
  const maxAttempts = 1200 // 20 minutes
  let attempts = 0
  let consecutiveErrors = 0
  const maxConsecutiveErrors = 5

  console.log(`[BackgroundKSelection] Starting polling for operation ${opId}`)

  while (attempts < maxAttempts && operationId.value === opId) {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 15000)

      const response = await fetch(`/api/k-selection/status/${opId}`, {
        signal: controller.signal
      })
      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`Status check failed: ${response.status}`)
      }

      const status = await response.json()
      consecutiveErrors = 0

      if (status.status === 'completed') {
        console.log('[BackgroundKSelection] Analysis completed successfully')
        return status.result
      } else if (status.status === 'failed') {
        throw new Error(status.error || 'K-selection analysis failed')
      } else if (status.status === 'not_found') {
        throw new Error('K-selection analysis operation not found')
      } else if (status.status === 'running') {
        console.log(`[BackgroundKSelection] Still running, elapsed: ${status.elapsed_time?.toFixed(2)}s`)
      }

      // Dynamic polling interval
      let pollInterval = 1000
      if (attempts > 30) pollInterval = 2000
      if (attempts > 120) pollInterval = 5000

      await new Promise(resolve => setTimeout(resolve, pollInterval))
      attempts++
    } catch (err: any) {
      if (operationId.value !== opId) {
        console.log('[BackgroundKSelection] Polling stopped - operation changed')
        return null
      }

      consecutiveErrors++
      console.error(`[BackgroundKSelection] Polling error (${consecutiveErrors}/${maxConsecutiveErrors}):`, err.message)

      if (consecutiveErrors >= maxConsecutiveErrors) {
        throw new Error(`K-selection failed after ${consecutiveErrors} consecutive errors: ${err.message}`)
      }

      const waitTime = Math.min(2000 * consecutiveErrors, 10000)
      await new Promise(resolve => setTimeout(resolve, waitTime))
      attempts++
    }
  }

  if (operationId.value !== opId) {
    return null // Aborted
  }

  throw new Error(`K-selection analysis timed out after ${Math.floor(maxAttempts / 60)} minutes`)
}

export const useBackgroundKSelection = () => {
  /**
   * Start a k-selection operation. Polling runs at module scope and survives navigation.
   * Returns the operation ID.
   */
  const startOperation = (opId: string) => {
    // Clear any previous results
    completedResults.value = null
    error.value = null
    operationId.value = opId
    isRunning.value = true

    // Start polling in the background
    pollingPromise = (async () => {
      try {
        const results = await pollForCompletion(opId)
        if (results && operationId.value === opId) {
          completedResults.value = results
          isRunning.value = false
          console.log('[BackgroundKSelection] Results stored globally')

          // Notify mounted component if callback is registered
          if (onCompleteCallback) {
            onCompleteCallback(results)
          }
        } else {
          isRunning.value = false
        }
      } catch (err: any) {
        if (operationId.value === opId) {
          error.value = err.message
          isRunning.value = false
          console.error('[BackgroundKSelection] Operation failed:', err.message)

          if (onErrorCallback) {
            onErrorCallback(err.message)
          }
        }
      } finally {
        pollingPromise = null
      }
    })()
  }

  /**
   * Abort the current operation. Sends abort to backend.
   */
  const abortOperation = async () => {
    const currentOpId = operationId.value
    if (currentOpId) {
      // Clear state first so polling loop exits
      operationId.value = null
      isRunning.value = false
      completedResults.value = null
      error.value = null

      // Then tell backend to abort
      try {
        await fetch(`/api/abort/${currentOpId}`, { method: 'POST' })
        console.log('[BackgroundKSelection] Backend abort sent')
      } catch (err) {
        console.error('[BackgroundKSelection] Backend abort failed:', err)
      }
    }
  }

  /**
   * Register callbacks for when results arrive (call from component setup).
   * Returns an unregister function.
   */
  const onComplete = (callback: (results: KSelectionResults) => void) => {
    onCompleteCallback = callback
    return () => { onCompleteCallback = null }
  }

  const onError = (callback: (error: string) => void) => {
    onErrorCallback = callback
    return () => { onErrorCallback = null }
  }

  /**
   * Consume completed results (resets them so they aren't re-processed).
   */
  const consumeResults = (): KSelectionResults | null => {
    const results = completedResults.value
    completedResults.value = null
    return results
  }

  /**
   * Consume error (resets it).
   */
  const consumeError = (): string | null => {
    const err = error.value
    error.value = null
    return err
  }

  return {
    // State (readonly for external consumers)
    operationId: readonly(operationId),
    isRunning: readonly(isRunning),
    hasResults: readonly(completedResults),
    hasError: readonly(error),

    // Actions
    startOperation,
    abortOperation,
    onComplete,
    onError,
    consumeResults,
    consumeError,
  }
}
