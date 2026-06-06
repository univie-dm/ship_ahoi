import { ref, computed, reactive, watch } from 'vue'
import { useFileUpload } from '~/composables/useFileUpload'

interface ColumnConfig {
  name: string
  samples: any[]
  dataType: string
  isCategorical: boolean
  missingCount: number
  usage: 'feature' | 'label' | 'ignore'
  normalize: boolean
}

interface FileData {
  type: 'upload'
  file: File
  name: string
  data: number[][]
  headers: string[]
  rowCount: number
  columnCount: number
  fileStats: {
    rows: number
    columns: number
    missingValues: number
    hasHeaders: boolean
  }
  hasHeaders: boolean
  missingValueStrategy: string
  normalization: string
  categoricalColumns?: Set<number>
  columnTypes?: string[]
  featureColumns?: number[]
  labelColumns?: number[]
  ignoredColumns?: number[]
  rawData?: any[][]
  fileId?: string
  backendMetadata?: any
  useBackend?: boolean
}

export function useColumnConfiguration() {
  const { detectColumnTypes, countMissingValues } = useFileUpload()
  
  const columnConfig = ref<ColumnConfig[]>([])
  
  // Computed properties for column counts
  const featureColumns = computed(() => 
    columnConfig.value.filter(col => col.usage === 'feature')
  )
  
  const labelColumns = computed(() => 
    columnConfig.value.filter(col => col.usage === 'label')
  )
  
  const ignoredColumns = computed(() => 
    columnConfig.value.filter(col => col.usage === 'ignore')
  )
  
  const normalizedColumns = computed(() => 
    columnConfig.value.filter(col => col.usage === 'feature' && col.normalize && !col.isCategorical)
  )
  
  // Initialize column configuration from file data
  const initializeColumnConfig = (fileData: FileData) => {
    if (!fileData.headers || !fileData.rawData) return
    
    const startRow = fileData.hasHeaders ? 1 : 0
    const dataRows = fileData.rawData.slice(startRow)
    
    columnConfig.value = fileData.headers.map((header, index) => {
      const columnData = dataRows.map(row => row[index])
      const nonNullData = columnData.filter(val => val !== null && val !== undefined && val !== '')
      
      // Detect data type
      const dataType = detectColumnTypes([columnData])[0] || 'text'
      const isCategorical = dataType === 'categorical' || dataType === 'text'
      
      // Count missing values
      const missingCount = countMissingValues([columnData])[0] || 0
      
      // Sample values for preview
      const samples = nonNullData.slice(0, 5)
      
      // Default configuration
      const defaultUsage = isCategorical && nonNullData.length > 0 && new Set(nonNullData).size < 20 
        ? 'label' 
        : 'feature'
      
      return {
        name: header,
        samples,
        dataType,
        isCategorical,
        missingCount,
        usage: defaultUsage,
        normalize: !isCategorical && dataType !== 'text'
      }
    })
  }
  
  // Bulk actions
  const selectAllAsFeatures = () => {
    columnConfig.value.forEach(col => {
      col.usage = 'feature'
    })
  }
  
  const selectOnlyNumericAsFeatures = () => {
    columnConfig.value.forEach(col => {
      if (col.dataType === 'numeric' || col.dataType === 'integer' || col.dataType === 'float') {
        col.usage = 'feature'
      } else {
        col.usage = 'ignore'
      }
    })
  }
  
  const clearAllSelections = () => {
    columnConfig.value.forEach(col => {
      col.usage = 'ignore'
    })
  }
  
  // Get configuration summary
  const getConfigurationSummary = () => {
    return {
      featureColumns: featureColumns.value.map((col, index) => ({ 
        ...col, 
        originalIndex: columnConfig.value.indexOf(col) 
      })),
      labelColumns: labelColumns.value.map((col, index) => ({ 
        ...col, 
        originalIndex: columnConfig.value.indexOf(col) 
      })),
      ignoredColumns: ignoredColumns.value.map((col, index) => ({ 
        ...col, 
        originalIndex: columnConfig.value.indexOf(col) 
      })),
      normalizedColumns: normalizedColumns.value.map((col, index) => ({ 
        ...col, 
        originalIndex: columnConfig.value.indexOf(col) 
      }))
    }
  }
  
  // Process data based on configuration
  const processDataWithConfiguration = (fileData: FileData, missingValueStrategy: string = 'keep', normalization: string = 'none') => {
    if (!fileData.data || !columnConfig.value.length) {
      throw new Error('No data or configuration available')
    }
    
    // Start with original data
    let processedData = fileData.data
    const startRow = fileData.hasHeaders ? 1 : 0
    
    // Get data rows (skip headers if present)
    let dataRows = processedData.slice(startRow)
    
    // Extract feature columns based on configuration
    const featureCols = featureColumns.value
      .map((col, index) => ({ ...col, originalIndex: columnConfig.value.indexOf(col) }))
    
    if (featureCols.length === 0) {
      throw new Error('No feature columns selected for clustering')
    }
    
    // Extract only feature column data
    const featureData = dataRows.map((row: any[]) => 
      featureCols.map((col: any) => row[col.originalIndex])
    )
    
    // Convert to numeric data (handling missing values)
    const numericData = featureData.map((row: any[]) => 
      row.map((cell: any) => {
        if (cell === null || cell === undefined || cell === '' || 
            String(cell) === 'null' || String(cell) === 'NaN' || String(cell) === 'N/A') {
          return NaN
        }
        const num = parseFloat(String(cell))
        return isNaN(num) ? NaN : num
      })
    )
    
    // Apply missing value handling
    let finalData = numericData
    if (missingValueStrategy === 'drop') {
      finalData = numericData.filter(row => !row.some(val => isNaN(val)))
    } else if (missingValueStrategy === 'mean') {
      // Calculate means for each column
      const columnMeans = featureCols.map((_, colIndex) => {
        const columnValues = numericData
          .map(row => row[colIndex])
          .filter(val => !isNaN(val))
        return columnValues.length > 0 
          ? columnValues.reduce((sum, val) => sum + val, 0) / columnValues.length 
          : 0
      })
      
      finalData = numericData.map(row => 
        row.map((val, colIndex) => isNaN(val) ? columnMeans[colIndex] : val)
      )
    }
    // For 'keep', we leave NaN values as is
    
    // Apply normalization to selected columns
    if (normalization && normalization !== 'none') {
      const columnsToNormalize = featureCols
        .map((col: any, index: number) => ({ ...col, dataIndex: index }))
        .filter((col: any) => col.normalize && !col.isCategorical)
        .map((col: any) => col.dataIndex)
      
      if (columnsToNormalize.length > 0) {
        // Apply normalization logic here
        if (normalization === 'standard') {
          columnsToNormalize.forEach(colIndex => {
            const columnValues = finalData.map(row => row[colIndex]).filter(val => !isNaN(val))
            if (columnValues.length > 0) {
              const mean = columnValues.reduce((sum, val) => sum + val, 0) / columnValues.length
              const std = Math.sqrt(
                columnValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / columnValues.length
              )
              if (std > 0) {
                finalData = finalData.map(row => {
                  const newRow = [...row]
                  if (!isNaN(newRow[colIndex])) {
                    newRow[colIndex] = (newRow[colIndex] - mean) / std
                  }
                  return newRow
                })
              }
            }
          })
        } else if (normalization === 'minmax') {
          columnsToNormalize.forEach(colIndex => {
            const columnValues = finalData.map(row => row[colIndex]).filter(val => !isNaN(val))
            if (columnValues.length > 0) {
              const min = Math.min(...columnValues)
              const max = Math.max(...columnValues)
              if (max > min) {
                finalData = finalData.map(row => {
                  const newRow = [...row]
                  if (!isNaN(newRow[colIndex])) {
                    newRow[colIndex] = (newRow[colIndex] - min) / (max - min)
                  }
                  return newRow
                })
              }
            }
          })
        }
      }
    }
    
    // Create feature headers from the feature columns
    const featureHeaders = featureCols.map((col: any) => col.name)
    
    return {
      data: finalData,
      headers: featureHeaders,
      rowCount: finalData.length,
      columnCount: featureHeaders.length,
      featureColumns: featureCols,
      configuration: getConfigurationSummary()
    }
  }
  
  return {
    columnConfig,
    featureColumns,
    labelColumns,
    ignoredColumns,
    normalizedColumns,
    initializeColumnConfig,
    selectAllAsFeatures,
    selectOnlyNumericAsFeatures,
    clearAllSelections,
    getConfigurationSummary,
    processDataWithConfiguration
  }
} 