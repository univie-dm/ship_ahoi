import { ref, computed, type Ref } from 'vue'
import type { ClusterRun } from './useGlobalState'

export const useHistoryFilters = (runs: Ref<ClusterRun[]>) => {
  // Filter state
  const filterDataset = ref('')
  const filterAlgorithm = ref('')
  const sortBy = ref('timestamp')
  
  // Computed unique values for filter options
  const uniqueDatasets = computed(() => {
    const datasets = runs.value.map(run => run.dataset)
    return [...new Set(datasets)].sort()
  })

  const uniqueAlgorithms = computed(() => {
    const algorithms = runs.value.map(run => run.treeType)
    return [...new Set(algorithms)].sort()
  })

  // Filtered and sorted runs
  const filteredRuns = computed(() => {
    let filteredData = [...runs.value]

    // Apply filters
    if (filterDataset.value) {
      filteredData = filteredData.filter(run => run.dataset === filterDataset.value)
    }
    if (filterAlgorithm.value) {
      filteredData = filteredData.filter(run => run.treeType === filterAlgorithm.value)
    }

    // Apply sorting
    filteredData.sort((a, b) => {
      switch (sortBy.value) {
        case 'timestamp':
          return b.timestamp.getTime() - a.timestamp.getTime()
        case 'dataset':
          return a.dataset.localeCompare(b.dataset)
        case 'treeType':
          return a.treeType.localeCompare(b.treeType)
        case 'selectedK':
          return a.selectedK - b.selectedK
        case 'silhouetteScore':
          const aScore = a.metrics?.silhouetteScore || 0
          const bScore = b.metrics?.silhouetteScore || 0
          return bScore - aScore
        case 'dbIndex':
          const aDB = a.metrics?.dbIndex || Infinity
          const bDB = b.metrics?.dbIndex || Infinity
          return aDB - bDB // Lower is better for DB Index
        case 'calinskiHarabasz':
          const aCH = a.metrics?.calinskiHarabasz || 0
          const bCH = b.metrics?.calinskiHarabasz || 0
          return bCH - aCH // Higher is better for Calinski-Harabasz
        case 'ari':
          const aARI = a.metrics?.ari ?? -1
          const bARI = b.metrics?.ari ?? -1
          return bARI - aARI // Higher is better for ARI
        case 'discoScore':
          const aDisco = a.metrics?.discoScore || 0
          const bDisco = b.metrics?.discoScore || 0
          return bDisco - aDisco // Higher is better
        default:
          return 0
      }
    })

    return filteredData
  })

  // Reset all filters
  const clearFilters = () => {
    filterDataset.value = ''
    filterAlgorithm.value = ''
    sortBy.value = 'timestamp'
  }

  return {
    // State
    filterDataset,
    filterAlgorithm,
    sortBy,
    
    // Computed
    uniqueDatasets,
    uniqueAlgorithms,
    filteredRuns,
    
    // Methods
    clearFilters
  }
}