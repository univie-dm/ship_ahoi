// File upload utility for handling both JSON and CSV files
// Features:
// - Automatic header detection for CSV files
// - Proper CSV parsing with quoted values and escaped quotes
// - File size validation (configurable limit)
// - Comprehensive error handling and validation
// - Support for both JSON and CSV formats
// - Missing value detection and handling
// - Data normalization options
// - One-hot encoding for categorical variables
// - Backend API integration for improved scalability

import { ref } from 'vue'
import { useFileUploadAPI } from './useFileUploadAPI'
import { useDebugUtils } from '~/composables/useDebugUtils'

// Determine if we should fallback to frontend processing based on error type
const shouldFallbackToFrontend = (error: any): boolean => {
  const errorMessage = error?.message?.toLowerCase() || ''
  
  // Always fallback for network connectivity issues
  if (error instanceof TypeError && errorMessage.includes('fetch')) {
    return true
  }
  
  // Always fallback for connection refused (backend not running)
  if (errorMessage.includes('connection refused') || 
      errorMessage.includes('network error') ||
      errorMessage.includes('cannot connect')) {
    return true
  }
  
  // Fallback for CORS issues (development environment)
  if (errorMessage.includes('cors')) {
    return true
  }
  
  // Fallback for timeout errors
  if (errorMessage.includes('timeout')) {
    return true
  }
  
  // DO NOT fallback for file format errors - these should be consistent
  if (errorMessage.includes('unsupported file format') ||
      errorMessage.includes('invalid file') ||
      errorMessage.includes('file too large')) {
    return false
  }
  
  // DO NOT fallback for server configuration errors
  if (errorMessage.includes('500') || 
      errorMessage.includes('internal server error') ||
      errorMessage.includes('configuration')) {
    return false
  }
  
  // DO NOT fallback for authentication/authorization errors
  if (errorMessage.includes('401') || 
      errorMessage.includes('403') ||
      errorMessage.includes('unauthorized') ||
      errorMessage.includes('forbidden')) {
    return false
  }
  
  // Fallback for other 4xx errors (client errors that might work with frontend)
  if (errorMessage.includes('400') || 
      errorMessage.includes('404') ||
      errorMessage.includes('bad request')) {
    return true
  }
  
  // Default: fallback for unknown errors (conservative approach)
  return true
}

export function useFileUpload() {
  const fileUploadAPI = useFileUploadAPI()
  const { debug, debugWarn } = useDebugUtils()
  
  // Configuration flag to enable backend processing
  const USE_BACKEND_PROCESSING = ref(true)
  
  // State management for preventing duplicate processing
  const processingState = ref<Map<string, { isProcessing: boolean, attempts: number }>>(new Map())
  
  // Simple circuit breaker to prevent repeated failures
  const getProcessingState = (fileKey: string) => {
    const state = processingState.value.get(fileKey)
    if (!state) {
      const newState = { isProcessing: false, attempts: 0 }
      processingState.value.set(fileKey, newState)
      return newState
    }
    return state
  }
  
  const canProcessFile = (fileKey: string): boolean => {
    const state = getProcessingState(fileKey)
    // Prevent processing if already in progress or too many attempts
    if (state.isProcessing) {
      debug(`File ${fileKey} is already being processed`)
      return false
    }
    if (state.attempts >= 3) {
      debug(`File ${fileKey} has failed too many times (${state.attempts} attempts)`)
      return false
    }
    return true
  }
  
  const startProcessing = (fileKey: string) => {
    const state = getProcessingState(fileKey)
    state.isProcessing = true
    state.attempts += 1
  }
  
  const finishProcessing = (fileKey: string, success: boolean) => {
    const state = getProcessingState(fileKey)
    state.isProcessing = false
    if (success) {
      state.attempts = 0 // Reset attempts on success
    }
  }
  
  // Enhanced file upload handler that can use backend or frontend processing
  const handleFileUploadEnhanced = async (file: File, useBackend: boolean = USE_BACKEND_PROCESSING.value): Promise<{
    data: number[][];
    fileName: string;
    fileType: string;
    hasHeaders?: boolean;
    rowCount: number;
    columnCount: number;
    categoricalColumns?: Set<number>;
    fileId?: string;
    backendMetadata?: any;
  }> => {
    debug('=== ENHANCED FILE UPLOAD CALLED ===')
    debug('File:', { name: file.name, size: file.size, type: file.type })
    debug('USE_BACKEND_PROCESSING flag:', USE_BACKEND_PROCESSING.value)
    debug('useBackend parameter:', useBackend)
    debug('Will attempt backend processing:', useBackend)
    
    // Create a unique key for this file
    const fileKey = `${file.name}-${file.size}-${file.lastModified}`
    
    // Check if we can process this file
    if (!canProcessFile(fileKey)) {
      throw new Error(`File ${file.name} is already being processed or has failed too many times`)
    }
    
    // Start processing tracking
    startProcessing(fileKey)
    
    try {
      if (useBackend) {
        try {
        // Test backend connection first
        debug('[Backend] Testing connection before upload...')
        const connectionTest = await fileUploadAPI.testConnection()
        
        if (!connectionTest.connected) {
          throw new Error(`Backend connection failed: ${connectionTest.message}`)
        }
        
        debug('[Backend] Connection test successful, proceeding with upload')
        
        // Use backend processing
        const uploadResponse = await fileUploadAPI.uploadFile(file)
        
        const result = {
          data: uploadResponse.data,
          headers: uploadResponse.headers, // Include the headers from backend!
          fileName: uploadResponse.file_info.filename,
          fileType: uploadResponse.file_info.extension.substring(1), // Remove the dot
          hasHeaders: uploadResponse.has_headers,
          rowCount: uploadResponse.row_count,
          columnCount: uploadResponse.column_count,
          categoricalColumns: new Set(
            uploadResponse.column_info
              .map((col, index) => col.is_categorical ? index : -1)
              .filter(index => index !== -1)
          ),
          fileId: uploadResponse.file_id,
          backendMetadata: {
            columnInfo: uploadResponse.column_info,
            fileInfo: uploadResponse.file_info,
            missingValueCount: uploadResponse.missing_value_count,
            dataTypes: uploadResponse.data_types,
            encoding: uploadResponse.encoding,
            separator: uploadResponse.separator
          }
        }
        
        // Mark as successful
        finishProcessing(fileKey, true)
        
        return result
      } catch (error) {
        console.error('=== BACKEND PROCESSING FAILURE ===')
        console.error('Error type:', error?.constructor?.name)
        console.error('Error message:', error?.message)
        console.error('Error details:', error)
        console.error('File info:', { name: file.name, size: file.size, type: file.type })
        console.error('Backend API URL:', 'http://localhost:8000/api/data/upload')
        
        // Check if it's a network error
        if (error instanceof TypeError && error.message.includes('fetch')) {
          console.error('NETWORK ERROR: Cannot connect to backend server')
          console.error('Ensure backend is running at http://localhost:8000')
        }
        
        // Check if it's a CORS error
        if (error instanceof TypeError && error.message.includes('CORS')) {
          console.error('CORS ERROR: Cross-origin request blocked')
        }
        
        // Check if it's a server error
        if (error?.message?.includes('500') || error?.message?.includes('Internal Server Error')) {
          console.error('SERVER ERROR: Backend processing failed with internal error')
        }
        
        // Determine if we should fallback based on error type
        const shouldFallback = shouldFallbackToFrontend(error)
        
        if (!shouldFallback) {
          console.error('=== CRITICAL BACKEND ERROR - NOT FALLING BACK ===')
          console.error('This error suggests a configuration or server issue that should be fixed')
          console.error('Consider checking backend server status and configuration')
          throw error // Re-throw the error instead of falling back
        }
        
        console.error('=== FALLING BACK TO FRONTEND PROCESSING ===')
        console.warn('Backend processing failed, falling back to frontend:', error?.message || error)
        
        // Fall back to frontend processing
        return handleFileUpload(file)
      }
    } else {
      // Use original frontend processing
      debug('[Frontend] Backend processing disabled, using frontend processing')
      const result = await handleFileUpload(file)
      finishProcessing(fileKey, true)
      return result
    }
    } catch (error) {
      finishProcessing(fileKey, false)
      throw error
    }
  }
  
  // Enhanced data processing that can use backend APIs
  const processDataEnhanced = async (
    fileId: string, 
    config: {
      missingValueStrategy?: string;
      normalization?: string;
      categoricalEncoding?: string;
      featureColumns?: number[];
      labelColumns?: number[];
      ignoredColumns?: number[];
      columnConfigs?: any[];
    }
  ) => {
    try {
      const processingConfig: any = {
        missing_value_strategy: config.missingValueStrategy || 'keep',
        normalization: config.normalization || 'none',
        categorical_encoding: config.categoricalEncoding || 'label',
        feature_columns: config.featureColumns || [],
        label_columns: config.labelColumns || [],
        ignored_columns: config.ignoredColumns || [],
        columns: config.columnConfigs || []
      }
      
      return await fileUploadAPI.processData(fileId, processingConfig)
    } catch (error) {
      console.error('Backend data processing failed:', error)
      throw error
    }
  }
  const parseCSV = async (csvText: string): Promise<{ data: number[][], categoricalColumns: Set<number>, hasHeadersActually: boolean, detectedHeaders?: string[] }> => {
    // More efficient line splitting for large files
    const lines = csvText.trim().split(/\r?\n/);
    const data: number[][] = [];
    const categoricalColumnMaps: Map<string, number>[] = [];
    const categoricalColumnNextId: number[] = [];
    const categoricalColumnsDetected = new Set<number>();

    if (lines.length === 0) {
      throw new Error('CSV file is empty');
    }

    const firstLineOriginal = lines[0].trim();
    const firstLineValues = parseCSVLine(firstLineOriginal);

    let startIndex = 0;
    let actualHeadersDetected = false;
    let detectedHeaders: string[] = [];

    // Header detection: if any cell in the first line is purely non-numeric (and not just a number-as-string)
    // it's considered a header. parseFloat will return NaN for such strings.
    if (firstLineValues.some(val => isNaN(parseFloat(val)))) {
      actualHeadersDetected = true;
      startIndex = 1;
      detectedHeaders = firstLineValues.map(val => String(val).trim());
      debug(`CSV headers detected and skipped: ${firstLineValues.join(', ')}`);
    }
    
    // Process lines with adaptive batching for better performance
    const adaptiveBatchSize = Math.min(500, Math.max(50, Math.floor(10000 / firstLineValues.length))); // Smaller batches for wider data
    let processedCount = 0;
    
    for (let batchStart = startIndex; batchStart < lines.length; batchStart += adaptiveBatchSize) {
      const batchEnd = Math.min(batchStart + adaptiveBatchSize, lines.length);
      
      // Process batch in chunks to avoid blocking
      const batchData: number[][] = [];
      for (let i = batchStart; i < batchEnd; i++) {
        const line = lines[i].trim();
        if (!line) continue; // Skip empty lines

      const values = parseCSVLine(line);
      const numericValues: number[] = [];

      // Ensure all rows have the same number of columns as the first data row (or header row if no data)
      const expectedColumnCount = (data.length > 0 ? data[0].length : firstLineValues.length);
      if (values.length !== expectedColumnCount && i > startIndex) { // Check only after the first data row is processed
          throw new Error(`Row ${i + 1} has ${values.length} columns, but expected ${expectedColumnCount} columns based on previous rows.`);
      }
      if (i === startIndex && values.length !== firstLineValues.length && actualHeadersDetected) {
          throw new Error(`First data row (line ${i + 1}) has ${values.length} columns, but header has ${firstLineValues.length} columns.`);
      }


      for (let colIndex = 0; colIndex < values.length; colIndex++) {
        const val = values[colIndex].trim(); // Trim individual values
        const num = parseFloat(val);

        if (!isNaN(num)) {
          numericValues.push(num);
        } else {
          // It's a string that couldn't be parsed as a float, treat as categorical
          categoricalColumnsDetected.add(colIndex);
          if (!categoricalColumnMaps[colIndex]) {
            categoricalColumnMaps[colIndex] = new Map<string, number>();
            categoricalColumnNextId[colIndex] = 0;
          }
          if (!categoricalColumnMaps[colIndex].has(val)) {
            categoricalColumnMaps[colIndex].set(val, categoricalColumnNextId[colIndex]);
            categoricalColumnNextId[colIndex]++;
          }
          numericValues.push(categoricalColumnMaps[colIndex].get(val)!);
        }
      }
        batchData.push(numericValues);
      }
      
      // Add batch to main data
      data.push(...batchData);
      processedCount += batchData.length;
      
      // Yield control periodically for large files
      if (processedCount % 1000 === 0 && lines.length > 5000) {
        await new Promise(resolve => setTimeout(resolve, 0));
      }
    }

    if (data.length === 0) {
        if (actualHeadersDetected && lines.length === 1) {
            throw new Error('CSV file only contains a header row. No data found.');
        }
        throw new Error('No valid numeric data found in CSV file after processing.');
    }
    
    if (categoricalColumnsDetected.size > 0) {
      debug(`CSV parsing: Detected and converted text to numbers in columns (0-indexed): ${Array.from(categoricalColumnsDetected).join(', ')}`);
    }

    return { data, categoricalColumns: categoricalColumnsDetected, hasHeadersActually: actualHeadersDetected, detectedHeaders };
  };

  // Helper function to parse a single CSV line with proper quote handling (optimized)
  const parseCSVLine = (line: string): string[] => {
    const values: string[] = [];
    let current = '';
    let inQuotes = false;
    let quoteChar = ''; // Can be ' or "
    
    // Use a more efficient loop for better performance
    const lineLength = line.length;
    for (let i = 0; i < lineLength; i++) {
      const char = line[i];
      const nextChar = i + 1 < lineLength ? line[i + 1] : '';
      
      if (!inQuotes) {
        if (char === '"' || char === "'") {
          inQuotes = true;
          quoteChar = char;
        } else if (char === ',') {
          values.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      } else { // Inside quotes
        if (char === quoteChar) {
          if (nextChar === quoteChar) { // Escaped quote (e.g., "" or '')
            current += char;
            i++; // Skip the second quote of the pair
          } else {
            // End of quoted section
            inQuotes = false;
            // quoteChar = ''; // Not strictly necessary to reset here
          }
        } else {
          current += char;
        }
      }
    }
    // Add the last value
    values.push(current.trim());
    
    return values;
  };

  const parseJSON = (jsonText: string): { data: number[][], categoricalColumns: Set<number> } => {
    let parsed: any[][];
    try {
      parsed = JSON.parse(jsonText);
    } catch (e: any) {
      throw new Error(`Invalid JSON format: ${e.message}`);
    }

    if (!Array.isArray(parsed)) {
      throw new Error('JSON root must be an array.');
    }
    if (parsed.length === 0) {
      return { data: [], categoricalColumns: new Set() }; // Handle empty array case
    }
    // Check if it's an array of arrays (2D)
    if (!parsed.every(row => Array.isArray(row))) {
        // Allow array of objects if they can be consistently converted, or throw error
        // For now, strictly expect array of arrays for simplicity matching CSV structure.
        throw new Error('JSON must contain a 2D array (array of arrays). Array of objects not directly supported by this parser.');
    }

    const resultData: number[][] = [];
    const categoricalColumnMaps: Map<string, number>[] = []; // One map per column index
    const categoricalColumnNextId: number[] = []; // Next ID for each column
    const categoricalColumnsDetected = new Set<number>();
    let expectedColumnCount: number | null = null;

    for (let i = 0; i < parsed.length; i++) {
      const rowArray = parsed[i]; // Already asserted to be an array
      if (i === 0) {
        expectedColumnCount = rowArray.length;
      } else if (rowArray.length !== expectedColumnCount) {
        throw new Error(`JSON data is not uniform: Row ${i + 1} has ${rowArray.length} columns, but expected ${expectedColumnCount}.`);
      }

      const currentRow: number[] = [];
      for (let j = 0; j < rowArray.length; j++) {
        const cellValue = rowArray[j];
        if (typeof cellValue === 'number' && !isNaN(cellValue)) {
          currentRow.push(cellValue);
        } else if (typeof cellValue === 'string') {
          categoricalColumnsDetected.add(j); // Mark column j as categorical
          if (!categoricalColumnMaps[j]) {
            categoricalColumnMaps[j] = new Map<string, number>();
            categoricalColumnNextId[j] = 0;
          }
          if (!categoricalColumnMaps[j].has(cellValue)) {
            categoricalColumnMaps[j].set(cellValue, categoricalColumnNextId[j]);
            categoricalColumnNextId[j]++;
          }
          currentRow.push(categoricalColumnMaps[j].get(cellValue)!);
        } else {
          // Handle null, boolean, or other types if necessary, or throw error
          throw new Error(`Unsupported data type at row ${i + 1}, column ${j + 1}: Found type '${typeof cellValue}' (value: '${cellValue}'). Only numbers and strings are supported.`);
        }
      }
      resultData.push(currentRow);
    }
    
    if (categoricalColumnsDetected.size > 0) {
      debug(`JSON parsing: Detected and converted text to numbers in columns (0-indexed): ${Array.from(categoricalColumnsDetected).join(', ')}`);
    }

    return { data: resultData, categoricalColumns: categoricalColumnsDetected };
  };

  const handleFileUpload = async (file: File): Promise<{
    data: number[][];
    fileName: string;
    fileType: string;
    hasHeaders?: boolean; // Specific to CSV
    rowCount: number;
    columnCount: number;
    categoricalColumns?: Set<number>; // Info about converted columns
    detectedHeaders?: string[]; // Headers detected during CSV parsing
  }> => {
    if (!file) {
      throw new Error('No file provided');
    }

    const fileName = file.name;
    const fileExtension = fileName.split('.').pop()?.toLowerCase();
    
    if (!fileExtension || !['json', 'csv'].includes(fileExtension)) {
      throw new Error('Only JSON and CSV files are supported');
    }

    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
      throw new Error(`File size (${(file.size / 1024 / 1024).toFixed(1)}MB) exceeds maximum allowed size of 100MB`);
    }

    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      // Add progress tracking
      reader.onprogress = (e) => {
        if (e.lengthComputable) {
          const progress = (e.loaded / e.total) * 100;
          debug(`File reading progress: ${progress.toFixed(1)}%`);
        }
      };
      
      reader.onload = async (e) => {
        try {
          const text = e.target?.result as string;
          let parsedResult: { data: number[][], categoricalColumns: Set<number>, detectedHeaders?: string[] };
          let csvActualHeaders = false;
          
          // Use requestIdleCallback for parsing to avoid blocking main thread
          const parseAsync = () => {
            return new Promise<{ data: number[][], categoricalColumns: Set<number>, hasHeadersActually?: boolean, detectedHeaders?: string[] }>((resolve, reject) => {
              const callback = async () => {
                try {
                  if (fileExtension === 'csv') {
                    const csvParseOutput = await parseCSV(text);
                    resolve({ 
                      data: csvParseOutput.data, 
                      categoricalColumns: csvParseOutput.categoricalColumns,
                      hasHeadersActually: csvParseOutput.hasHeadersActually,
                      detectedHeaders: csvParseOutput.detectedHeaders
                    });
                  } else { // JSON
                    const jsonParseOutput = parseJSON(text);
                    resolve({ 
                      data: jsonParseOutput.data, 
                      categoricalColumns: jsonParseOutput.categoricalColumns
                    });
                  }
                } catch (error) {
                  reject(error);
                }
              };
              
              if ('requestIdleCallback' in window) {
                requestIdleCallback(callback, { timeout: 1000 });
              } else {
                setTimeout(callback, 0);
              }
            });
          };
          
          const parseOutput = await parseAsync();
          parsedResult = { data: parseOutput.data, categoricalColumns: parseOutput.categoricalColumns, detectedHeaders: parseOutput.detectedHeaders };
          csvActualHeaders = parseOutput.hasHeadersActually || false;
          
          const data = parsedResult.data;

          // Allow empty JSON array `[]` or CSV that becomes empty after header removal
          if (data.length === 0) {
            if (fileExtension === 'json' && text.trim() === '[]') {
              // Valid empty JSON array
            } else if (fileExtension === 'csv' && csvActualHeaders && text.trim().split('\n').length === 1) {
              // Valid CSV with only a header row
            } else {
              throw new Error('File is empty or contains no valid data rows after processing.');
            }
          }
          
          let columnCount = 0;
          if (data.length > 0) {
            columnCount = data[0].length;
            // Uniformity check is now inside parseCSV and parseJSON for earlier error detection
          }
          
          // Relaxed validation for rows/columns, specific checks can be done by consumer
          // if (data.length > 0) {
          //   if (data.length < 2) { 
          //     console.warn('Uploaded file has less than 2 data rows. This might be insufficient for some analyses.');
          //   }
          //   if (columnCount < 1) { 
          //      console.warn('Uploaded file has less than 1 data column. This might be insufficient for some analyses.');
          //   }
          // }
          
          resolve({
            data,
            fileName,
            fileType: fileExtension,
            ...(fileExtension === 'csv' && { hasHeaders: csvActualHeaders }),
            rowCount: data.length,
            columnCount: columnCount,
            categoricalColumns: parsedResult.categoricalColumns,
            detectedHeaders: parsedResult.detectedHeaders,
          });
        } catch (error) {
          reject(new Error(`Failed to parse ${fileExtension.toUpperCase()} file: ${error instanceof Error ? error.message : 'Unknown error'}`));
        }
      };
      
      reader.onerror = () => {
        reject(new Error('Failed to read file'));
      };
      
      reader.readAsText(file);
    });
  };

  // Missing value handling functions
  const handleMissingValues = (data: number[][], strategy: string = 'keep'): { data: number[][], removedRows: number } => {
    if (strategy === 'keep') {
      return { data, removedRows: 0 };
    }

    let processedData: number[][] = [];
    let removedRows = 0;

    switch (strategy) {
      case 'remove':
        processedData = data.filter(row => {
          const hasNaN = row.some(cell => isNaN(cell) || cell === null || cell === undefined);
          if (hasNaN) removedRows++;
          return !hasNaN;
        });
        break;

      case 'fill_mean':
        // Calculate means for each column
        const columnMeans = calculateColumnMeans(data);
        processedData = data.map(row => 
          row.map((cell, colIndex) => 
            isNaN(cell) || cell === null || cell === undefined ? columnMeans[colIndex] : cell
          )
        );
        break;

      case 'fill_median':
        // Calculate medians for each column
        const columnMedians = calculateColumnMedians(data);
        processedData = data.map(row => 
          row.map((cell, colIndex) => 
            isNaN(cell) || cell === null || cell === undefined ? columnMedians[colIndex] : cell
          )
        );
        break;

      case 'fill_zero':
        processedData = data.map(row => 
          row.map(cell => 
            isNaN(cell) || cell === null || cell === undefined ? 0 : cell
          )
        );
        break;

      default:
        processedData = data;
    }

    return { data: processedData, removedRows };
  };

  // Calculate column means (ignoring NaN values)
  const calculateColumnMeans = (data: number[][]): number[] => {
    if (data.length === 0) return [];
    
    const columnCount = data[0].length;
    const means: number[] = [];

    for (let col = 0; col < columnCount; col++) {
      const validValues = data
        .map(row => row[col])
        .filter(val => !isNaN(val) && val !== null && val !== undefined);
      
      const mean = validValues.length > 0 
        ? validValues.reduce((sum, val) => sum + val, 0) / validValues.length 
        : 0;
      means.push(mean);
    }

    return means;
  };

  // Calculate column medians (ignoring NaN values)
  const calculateColumnMedians = (data: number[][]): number[] => {
    if (data.length === 0) return [];
    
    const columnCount = data[0].length;
    const medians: number[] = [];

    for (let col = 0; col < columnCount; col++) {
      const validValues = data
        .map(row => row[col])
        .filter(val => !isNaN(val) && val !== null && val !== undefined)
        .sort((a, b) => a - b);
      
      let median = 0;
      if (validValues.length > 0) {
        const mid = Math.floor(validValues.length / 2);
        median = validValues.length % 2 === 0 
          ? (validValues[mid - 1] + validValues[mid]) / 2 
          : validValues[mid];
      }
      medians.push(median);
    }

    return medians;
  };

  // Normalization functions
  const normalizeData = (data: number[][], method: string = 'none'): number[][] => {
    if (method === 'none' || data.length === 0) {
      return data;
    }

    const columnCount = data[0].length;
    let normalizedData: number[][];

    switch (method) {
      case 'standard':
        // Z-score normalization: (x - mean) / std
        const means = calculateColumnMeans(data);
        const stds = calculateColumnStandardDeviations(data, means);
        
        normalizedData = data.map(row =>
          row.map((cell, colIndex) => {
            const std = stds[colIndex];
            return std > 0 ? (cell - means[colIndex]) / std : 0;
          })
        );
        break;

      case 'minmax':
        // Min-max normalization: (x - min) / (max - min)
        const { mins, maxs } = calculateColumnMinMax(data);
        
        normalizedData = data.map(row =>
          row.map((cell, colIndex) => {
            const range = maxs[colIndex] - mins[colIndex];
            return range > 0 ? (cell - mins[colIndex]) / range : 0;
          })
        );
        break;

      default:
        normalizedData = data;
    }

    return normalizedData;
  };

  // Calculate column standard deviations
  const calculateColumnStandardDeviations = (data: number[][], means: number[]): number[] => {
    if (data.length === 0) return [];
    
    const columnCount = data[0].length;
    const stds: number[] = [];

    for (let col = 0; col < columnCount; col++) {
      const validValues = data
        .map(row => row[col])
        .filter(val => !isNaN(val) && val !== null && val !== undefined);
      
      if (validValues.length <= 1) {
        stds.push(0);
        continue;
      }

      const variance = validValues.reduce((sum, val) => {
        const diff = val - means[col];
        return sum + (diff * diff);
      }, 0) / (validValues.length - 1);
      
      stds.push(Math.sqrt(variance));
    }

    return stds;
  };

  // Calculate column min and max values
  const calculateColumnMinMax = (data: number[][]): { mins: number[], maxs: number[] } => {
    if (data.length === 0) return { mins: [], maxs: [] };
    
    const columnCount = data[0].length;
    const mins: number[] = [];
    const maxs: number[] = [];

    for (let col = 0; col < columnCount; col++) {
      const validValues = data
        .map(row => row[col])
        .filter(val => !isNaN(val) && val !== null && val !== undefined);
      
      if (validValues.length === 0) {
        mins.push(0);
        maxs.push(0);
      } else {
        mins.push(Math.min(...validValues));
        maxs.push(Math.max(...validValues));
      }
    }

    return { mins, maxs };
  };

  // Count missing values in dataset
  const countMissingValues = (data: any[][]): number => {
    let count = 0;
    for (const row of data) {
      for (const cell of row) {
        if (cell === null || cell === undefined || cell === '' || 
            cell === 'null' || cell === 'NaN' || 
            (typeof cell === 'number' && isNaN(cell))) {
          count++;
        }
      }
    }
    return count;
  };

  // Detect column data types
  const detectColumnTypes = (data: any[][], hasHeaders: boolean = false): string[] => {
    if (data.length === 0) return [];
    
    const startRow = hasHeaders ? 1 : 0;
    const dataRows = data.slice(startRow);
    const columnCount = data[0].length;
    const types: string[] = [];

    for (let col = 0; col < columnCount; col++) {
      const columnValues = dataRows.map(row => row[col]).filter(val => 
        val !== null && val !== undefined && val !== '' && val !== 'null' && val !== 'NaN'
      );
      
      if (columnValues.length === 0) {
        types.push('empty');
        continue;
      }

      const numericCount = columnValues.filter(val => !isNaN(Number(val))).length;
      const numericRatio = numericCount / columnValues.length;

      if (numericRatio > 0.8) {
        // Check if it's integer or float
        const integerCount = columnValues.filter(val => Number.isInteger(Number(val))).length;
        const integerRatio = integerCount / numericCount;
        types.push(integerRatio > 0.9 ? 'integer' : 'numeric');
      } else if (numericRatio < 0.2) {
        // Check if it's boolean
        const booleanValues = columnValues.filter(val => 
          String(val).toLowerCase() === 'true' || 
          String(val).toLowerCase() === 'false' ||
          val === 0 || val === 1
        );
        types.push(booleanValues.length > columnValues.length * 0.8 ? 'boolean' : 'categorical');
      } else {
        types.push('mixed');
      }
    }

    return types;
  };

  // One-hot encoding for categorical columns
  const oneHotEncode = (data: number[][], categoricalColumns: Set<number>): { 
    data: number[][], 
    newColumnNames: string[], 
    categoricalMappings: Map<number, Map<number, string>> 
  } => {
    if (categoricalColumns.size === 0) {
      return { 
        data, 
        newColumnNames: [], 
        categoricalMappings: new Map() 
      };
    }

    const categoricalMappings = new Map<number, Map<number, string>>();
    const newColumnNames: string[] = [];
    let encodedData: number[][] = [];

    // First, identify unique values in categorical columns
    for (const colIndex of categoricalColumns) {
      const uniqueValues = new Set<number>();
      data.forEach(row => {
        if (row[colIndex] !== null && row[colIndex] !== undefined && !isNaN(row[colIndex])) {
          uniqueValues.add(row[colIndex]);
        }
      });

      const valueMapping = new Map<number, string>();
      const sortedValues = Array.from(uniqueValues).sort();
      sortedValues.forEach((value, index) => {
        valueMapping.set(value, `cat_${colIndex}_${index}`);
        newColumnNames.push(`Column_${colIndex}_${value}`);
      });
      
      categoricalMappings.set(colIndex, valueMapping);
    }

    // Transform data with one-hot encoding
    encodedData = data.map(row => {
      const newRow: number[] = [];
      
      // Add non-categorical columns first
      row.forEach((cell, colIndex) => {
        if (!categoricalColumns.has(colIndex)) {
          newRow.push(cell);
        }
      });

      // Add one-hot encoded categorical columns
      for (const colIndex of Array.from(categoricalColumns).sort()) {
        const mapping = categoricalMappings.get(colIndex)!;
        const cellValue = row[colIndex];
        
        // Create one-hot vector for this categorical column
        for (const [value] of mapping) {
          newRow.push(cellValue === value ? 1 : 0);
        }
      }

      return newRow;
    });

    return { data: encodedData, newColumnNames, categoricalMappings };
  };

  // === Unified processing for uploaded data (frontend + backend fallback) ===
  const processUploadedDataUnified = async (
    fileData: any,
    columnConfig: any[],
    options: { useBackend?: boolean } = {}
  ): Promise<{
    data: number[][];
    headers: string[];
    rowCount: number;
    columnCount: number;
    featureColumns: any[];
  }> => {
    if (!fileData) throw new Error('processUploadedDataUnified: fileData is required')

    const allowBackend = options.useBackend !== false && USE_BACKEND_PROCESSING.value && fileData.fileId

    if (allowBackend) {
      try {
        const featureColumnsIdx = columnConfig
          .filter((c: any) => c.usage === 'feature')
          .map((c: any, idx: number) => typeof c.originalIndex === 'number' ? c.originalIndex : (c.index ?? idx))
        const labelColumnsIdx = columnConfig
          .filter((c: any) => c.usage === 'label')
          .map((c: any, idx: number) => typeof c.originalIndex === 'number' ? c.originalIndex : (c.index ?? idx))
        const ignoredColumnsIdx = columnConfig
          .filter((c: any) => c.usage === 'ignore')
          .map((c: any, idx: number) => typeof c.originalIndex === 'number' ? c.originalIndex : (c.index ?? idx))

        const backendCfg = {
          missingValueStrategy: fileData.missingValueStrategy || 'keep',
          normalization: fileData.normalization || 'none',
          categoricalEncoding: 'onehot',
          featureColumns: featureColumnsIdx,
          labelColumns: labelColumnsIdx,
          ignoredColumns: ignoredColumnsIdx,
          columnConfigs: columnConfig.map((col: any, idx: number) => ({
            name: col.name,
            index: typeof col.originalIndex === 'number' ? col.originalIndex : (col.index ?? idx),
            data_type: col.dataType || 'numeric',
            usage: col.usage,
            normalize: !!col.normalize,
            is_categorical: !!col.isCategorical
          }))
        }

        const backendRes = await processDataEnhanced(fileData.fileId, backendCfg)
        return {
          data: backendRes.data,
          headers: backendRes.headers,
          rowCount: backendRes.row_count,
          columnCount: backendRes.column_count,
          featureColumns: columnConfig.filter((c: any) => c.usage === 'feature')
        }
      } catch (err) {
        console.warn('processUploadedDataUnified: backend processing failed, falling back to frontend', err)
      }
    }

    // ---------- Frontend processing fallback ----------
    const startRow = fileData.hasHeaders ? 1 : 0
    const rawRows: any[][] = fileData.parsedData || fileData.data || []
    const dataRows = rawRows.slice(startRow)

    const featureColumns = columnConfig
      .map((col: any, idx: number) => ({ ...col, originalIndex: typeof col.originalIndex === 'number' ? col.originalIndex : idx }))
      .filter((col: any) => col.usage === 'feature')

    if (featureColumns.length === 0) {
      throw new Error('No feature columns selected for clustering')
    }

    const featureData = dataRows.map((row: any[]) => featureColumns.map((col: any) => row[col.originalIndex]))

    const numericData = featureData.map((row: any[]) =>
      row.map((cell: any) => {
        if (
          cell === null || cell === undefined || cell === '' ||
          String(cell).toLowerCase() === 'null' || String(cell) === 'NaN' || String(cell).toLowerCase() === 'n/a'
        ) {
          return NaN
        }
        const num = parseFloat(String(cell))
        return isNaN(num) ? NaN : num
      })
    )

    const { data: cleanedData } = handleMissingValues(numericData, fileData.missingValueStrategy || 'keep')

    let finalData = cleanedData
    if (fileData.normalization && fileData.normalization !== 'none') {
      const colsToNorm = featureColumns
        .map((col: any, idx: number) => ({ ...col, dataIndex: idx }))
        .filter((col: any) => col.normalize && !col.isCategorical)
        .map((col: any) => col.dataIndex)

      if (colsToNorm.length > 0) {
        finalData = cleanedData.map((r) => [...r])
        const normSubset = cleanedData.map((r) => colsToNorm.map((ci) => r[ci]))
        const normed = normalizeData(normSubset, fileData.normalization)
        finalData.forEach((r, ri) => {
          colsToNorm.forEach((ci, subIdx) => {
            r[ci] = normed[ri][subIdx]
          })
        })
      }
    }

    const headers = featureColumns.map((c: any) => c.name || `Feature_${c.originalIndex}`)

    return {
      data: finalData,
      headers,
      rowCount: finalData.length,
      columnCount: headers.length,
      featureColumns
    }
  }

  return { 
    handleFileUpload, 
    parseCSV, 
    parseJSON,
    handleMissingValues,
    normalizeData,
    countMissingValues,
    detectColumnTypes,
    oneHotEncode,
    calculateColumnMeans,
    calculateColumnMedians,
    // Enhanced backend integration methods
    handleFileUploadEnhanced,
    processDataEnhanced,
    fileUploadAPI,
    USE_BACKEND_PROCESSING,
    // Unified processing export
    processUploadedDataUnified
  };
}
