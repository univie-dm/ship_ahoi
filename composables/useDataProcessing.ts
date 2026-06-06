// Data processing utilities for file upload
import { useDebugUtils } from '~/composables/useDebugUtils'

/**
 * Shared data processing utilities for file upload
 * Extracted from the working data-upload.vue implementation
 */
export function useDataProcessing() {
  const { debug, debugWarn, debugError, debugInfo } = useDebugUtils()
  
  /**
   * Setup preview data and headers from file upload result
   * This is the proven working logic from data-upload.vue
   */
  const setupPreview = (processResult: any, overrideHasHeaders?: boolean) => {
    debug('[setupPreview] Called with:', { 
      hasBackendMetadata: !!processResult.backendMetadata,
      hasHeaders: processResult.hasHeaders,
      dataLength: processResult.data?.length,
      overrideHasHeaders,
      firstRow: processResult.data?.[0]
    })
    
    let previewHeaders: string[] = []
    let previewData: any[][] = []
    let hasHeaders = false
    
    // Determine if headers were detected (prefer explicit override, then backend result)
    const headersDetected = overrideHasHeaders !== undefined ? overrideHasHeaders : processResult.hasHeaders
    
    if (processResult.backendMetadata) {
      // Backend processing - headers are already extracted and provided separately
      // IMPORTANT: Backend data does NOT include header row - it's pure data
      debug('[setupPreview] Backend processing detected')
      previewHeaders = processResult.headers || processResult.backendMetadata.columnInfo?.map((col: any, i: number) => col.name || `Column ${i + 1}`) || []
      previewData = processResult.data || []
      
      // If no headers provided by backend but we expect them, generate defaults
      if (previewHeaders.length === 0 && previewData.length > 0) {
        previewHeaders = Array.from({ length: previewData[0]?.length || 0 }, (_, i) => `Column ${i + 1}`)
      }
      
      hasHeaders = !!processResult.hasHeaders
      debug('[setupPreview] Backend result - Headers:', previewHeaders)
      debug('[setupPreview] Backend data rows (no header row included):', previewData.length)
    } else if (headersDetected && processResult.data.length > 0) {
      // Frontend processing with headers detected by CSV parser
      debug('[setupPreview] Frontend processing with headers')
      
      // CRITICAL FIX: Use detectedHeaders from CSV parser instead of re-extracting
      if (processResult.detectedHeaders && processResult.detectedHeaders.length > 0) {
        // Use the headers that were properly detected and extracted by the CSV parser
        previewHeaders = processResult.detectedHeaders.map((header: string, i: number) => {
          if (!header || header.trim() === '') {
            return `Column ${i + 1}`
          }
          return header.trim()
        })
        
        // Data is already clean (headers were already removed by CSV parser)
        previewData = processResult.data
        hasHeaders = true
        debug('[setupPreview] Using detected headers from CSV parser:', previewHeaders)
      } else {
        // Fallback to old method only if detectedHeaders not available
        debug('[setupPreview] No detectedHeaders available, falling back to first-row extraction')
        const firstRow = processResult.data[0] || []
        previewHeaders = firstRow.map((h: any, i: number) => {
          if (h === null || h === undefined) {
            return `Column ${i + 1}`
          }
          
          try {
            const headerStr = String(h).trim()
            // Validate header (not empty, not special values, reasonable length)
            if (headerStr && 
                headerStr !== 'null' && 
                headerStr !== 'undefined' && 
                headerStr !== 'NaN' &&
                headerStr.length > 0 &&
                headerStr.length < 100) {
              return headerStr
            }
          } catch (e) {
            debugWarn(`[setupPreview] Header conversion failed for column ${i}:`, e)
          }
          return `Column ${i + 1}`
        })
        
        // Remove header row from data
        previewData = processResult.data.slice(1)
        hasHeaders = true
        debug('[setupPreview] Frontend with headers - Extracted headers (fallback):', previewHeaders)
      }
    } else {
      // No headers - use all data and generate column names
      debug('[setupPreview] No headers detected')
      previewHeaders = Array.from({ length: processResult.data[0]?.length || 0 }, (_, i) => `Column ${i + 1}`)
      previewData = processResult.data || []
      hasHeaders = false
    }
    
    // Comprehensive validation and debugging
    if (previewData.length === 0) {
      debugWarn('[setupPreview] Warning: No preview data after processing')
    }
    
    if (previewHeaders.length === 0 && previewData.length > 0) {
      debugWarn('[setupPreview] Warning: No headers but data exists')
      previewHeaders = Array.from({ length: previewData[0]?.length || 0 }, (_, i) => `Column ${i + 1}`)
    }
    
    // Validate header-data alignment
    if (previewData.length > 0 && previewHeaders.length !== previewData[0]?.length) {
      debugError('[setupPreview] ERROR: Header count mismatch!', {
        headerCount: previewHeaders.length,
        dataColumnCount: previewData[0]?.length,
        headers: previewHeaders,
        firstDataRow: previewData[0]
      })
    }
    
    // Check for potential data loss (first row accidentally treated as headers)
    if (processResult.data.length > 0 && previewData.length === processResult.data.length - 1 && !processResult.backendMetadata) {
      const possibleHeaders = processResult.data[0]
      const hasStringHeaders = possibleHeaders?.some((cell: any) => {
        const str = String(cell).trim()
        return isNaN(parseFloat(str)) && str !== '' && str !== 'null'
      })
      
      if (hasStringHeaders) {
        debugInfo('[setupPreview] First row contains string values, correctly treated as headers')
      } else {
        debugWarn('[setupPreview] Warning: First row was skipped but may contain data:', possibleHeaders)
      }
    }
    
    debug('[setupPreview] Final result:', {
      headers: previewHeaders,
      dataRowCount: previewData.length,
      originalDataRowCount: processResult.data?.length,
      firstDataSample: previewData[0],
      hasHeadersFlag: hasHeaders,
      backendProcessed: !!processResult.backendMetadata,
      dataLossDetected: processResult.data?.length && previewData.length < processResult.data.length
    })
    
    // Critical data loss detection
    if (processResult.data?.length && previewData.length < processResult.data.length) {
      const lostRows = processResult.data.length - previewData.length
      console.error(`[setupPreview] CRITICAL: Lost ${lostRows} rows during processing!`)
      console.error('[setupPreview] Original data length:', processResult.data.length)
      console.error('[setupPreview] Preview data length:', previewData.length)
      console.error('[setupPreview] Backend metadata:', !!processResult.backendMetadata)
      console.error('[setupPreview] Headers detected:', headersDetected)
    }
    
    return {
      headers: previewHeaders,
      data: previewData,
      hasHeaders
    }
  }

  /**
   * Apply missing value strategy to data
   */
  const applyMissingValueStrategy = async (data: any[][], strategy: string): Promise<any[][]> => {
    if (strategy === 'keep' || data.length === 0) {
      return data
    }
    
    debug(`Applying missing value strategy: ${strategy}`)
    
    switch (strategy) {
      case 'remove':
        return data.filter(row => {
          return !row.some(cell => 
            cell === null || cell === undefined || cell === '' || 
            String(cell).toLowerCase() === 'null' || String(cell) === 'NaN' ||
            String(cell).toLowerCase() === 'n/a'
          )
        })
      
      case 'fill_mean':
        return fillWithColumnStats(data, 'mean')
      
      case 'fill_median':
        return fillWithColumnStats(data, 'median')
      
      case 'fill_zero':
        return data.map(row => 
          row.map(cell => isMissingValue(cell) ? 0 : cell)
        )
      
      default:
        console.warn(`Unknown missing value strategy: ${strategy}, keeping data as-is`)
        return data
    }
  }

  const isMissingValue = (cell: any): boolean => {
    return cell === null || cell === undefined || cell === '' || 
           String(cell).toLowerCase() === 'null' || String(cell) === 'NaN' ||
           String(cell).toLowerCase() === 'n/a' || 
           (typeof cell === 'number' && isNaN(cell))
  }

  const fillWithColumnStats = (data: any[][], statType: 'mean' | 'median'): any[][] => {
    if (data.length === 0) return data
    
    const columnCount = data[0].length
    const columnStats: number[] = []
    
    // Calculate stats for each column
    for (let col = 0; col < columnCount; col++) {
      const validValues = data
        .map(row => row[col])
        .filter(val => !isMissingValue(val) && !isNaN(parseFloat(String(val))))
        .map(val => parseFloat(String(val)))
      
      if (validValues.length === 0) {
        columnStats[col] = 0
      } else if (statType === 'mean') {
        columnStats[col] = validValues.reduce((sum, val) => sum + val, 0) / validValues.length
      } else { // median
        const sorted = [...validValues].sort((a, b) => a - b)
        const mid = Math.floor(sorted.length / 2)
        columnStats[col] = sorted.length % 2 === 0 
          ? (sorted[mid - 1] + sorted[mid]) / 2 
          : sorted[mid]
      }
    }
    
    // Fill missing values
    return data.map(row => 
      row.map((cell, colIndex) => {
        if (isMissingValue(cell)) {
          // Try to parse as number, fallback to stat value
          const numVal = parseFloat(String(cell))
          return isNaN(numVal) ? columnStats[colIndex] : numVal
        }
        return cell
      })
    )
  }

  return {
    setupPreview,
    applyMissingValueStrategy
  }
}