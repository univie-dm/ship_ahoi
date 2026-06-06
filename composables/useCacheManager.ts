import { ref } from 'vue'
import { useToast } from './useToast'

export interface CacheInfo {
  ship_cache: {
    num_cached_objects: number
    cached_datasets: Array<{
      key: string
      data_hash: string
      tree_type: string
      last_accessed: string
      access_count: string
    }>
  }
  umap_cache: {
    redis_cache_size: number
    total_cache_size: number
    estimated_memory_mb: number
    redis_cached_datasets: Array<{
      key: string
      data_shape: number[]
      computation_time: number
      age_minutes: number
    }>
  }
  tsne_cache: {
    redis_cache_size: number
    total_cache_size: number
    estimated_memory_mb: number
    redis_cached_datasets: Array<{
      key: string
      data_shape: number[]
      age_minutes: number
    }>
  }
  toy_dataset_cache: {
    cached_datasets: number
    cache_keys: string[]
  }
  total_cached_items: number
  estimated_total_memory_mb: number
}

export function useCacheManager() {
  const { addToast } = useToast()
  
  const isLoading = ref(false)
  const cacheInfo = ref<CacheInfo | null>(null)
  
  const getCacheInfo = async (): Promise<CacheInfo | null> => {
    isLoading.value = true
    try {
      const data = await $fetch('/api/cache/info')
      cacheInfo.value = data
      return data
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'Failed to fetch cache information'
      console.error('Error fetching cache info:', error)
      addToast(errorMessage, 'error')
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  const clearAllCaches = async (): Promise<boolean> => {
    isLoading.value = true
    try {
      const data = await $fetch('/api/cache/clear', {
        method: 'POST'
      })
      if (data.success) {
        addToast('All caches cleared successfully', 'success')
        // Refresh cache info
        await getCacheInfo()
        return true
      } else {
        throw new Error(data.message || 'Failed to clear caches')
      }
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'Failed to clear caches'
      console.error('Error clearing caches:', error)
      addToast(errorMessage, 'error')
      return false
    } finally {
      isLoading.value = false
    }
  }
  
  const clearUMAPCache = async (): Promise<boolean> => {
    isLoading.value = true
    try {
      const data = await $fetch('/api/cache/clear-umap', {
        method: 'POST'
      })
      if (data.success) {
        addToast('UMAP cache cleared successfully', 'success')
        // Refresh cache info
        await getCacheInfo()
        return true
      } else {
        throw new Error(data.message || 'Failed to clear UMAP cache')
      }
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'Failed to clear UMAP cache'
      console.error('Error clearing UMAP cache:', error)
      addToast(errorMessage, 'error')
      return false
    } finally {
      isLoading.value = false
    }
  }
  
  const getUMAPCacheInfo = async () => {
    isLoading.value = true
    try {
      return await $fetch('/api/cache/umap-info')
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'Failed to fetch UMAP cache information'
      console.error('Error fetching UMAP cache info:', error)
      addToast(errorMessage, 'error')
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  return {
    // State
    isLoading,
    cacheInfo,
    
    // Methods
    getCacheInfo,
    clearAllCaches,
    clearUMAPCache,
    getUMAPCacheInfo
  }
}