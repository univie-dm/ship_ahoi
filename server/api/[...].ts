/**
 * Nuxt Server API Proxy
 * 
 * Catches all /api/* requests from the client and forwards them to the FastAPI backend.
 * This prevents direct client-to-backend connections and allows proper environment-based configuration.
 */

import {
  defineEventHandler,
  getQuery,
  getHeaders,
  readBody,
  readRawBody,
  readMultipartFormData,
  setResponseStatus,
  setResponseHeader
} from 'h3'

// useRuntimeConfig is auto-imported by Nuxt

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const apiBase = config.apiBase || 'http://localhost:8000'
  
  // Log the backend URL being used (only in development/debug)
  console.log(`[Proxy] Using backend: ${apiBase}`)
  
  // Get the full path including /api/
  const path = event.path
  
  // Construct the backend URL (backend expects /api/* paths)
  const targetUrl = `${apiBase}${path}`
  
  // Get query parameters
  const query = getQuery(event)
  const queryString = new URLSearchParams(query as Record<string, string>).toString()
  const fullUrl = queryString ? `${targetUrl}?${queryString}` : targetUrl
  
  // Get request method and headers
  const method = event.method
  const headers = getHeaders(event)
  
  // Filter out headers that shouldn't be forwarded
  const forwardHeaders: Record<string, string> = {}
  const headersToSkip = ['host', 'connection', 'content-length']
  
  for (const [key, value] of Object.entries(headers)) {
    if (!headersToSkip.includes(key.toLowerCase()) && value) {
      forwardHeaders[key] = value
    }
  }
  
  try {
    // Handle request body for POST/PUT/PATCH
    let body: any = undefined
    if (['POST', 'PUT', 'PATCH'].includes(method)) {
      const contentType = headers['content-type']
      
      if (contentType?.includes('multipart/form-data')) {
        // Handle multipart form data (file uploads)
        body = await readMultipartFormData(event)
        
        // Convert to FormData for forwarding
        const formData = new FormData()
        if (body) {
          for (const part of body) {
            if (part.filename) {
              // File field
              const blob = new Blob([part.data], { type: part.type })
              formData.append(part.name || 'file', blob, part.filename)
            } else {
              // Regular field
              formData.append(part.name || '', part.data.toString())
            }
          }
        }
        body = formData
        
        // Remove content-type header to let fetch set it with boundary
        delete forwardHeaders['content-type']
      } else if (contentType?.includes('application/json')) {
        // Handle JSON
        body = await readBody(event)
      } else {
        // Handle other content types
        body = await readRawBody(event)
      }
    }
    
    // Forward the request to the backend
    console.log(`[Proxy] Forwarding ${method} request to: ${fullUrl}`)
    
    const response = await fetch(fullUrl, {
      method,
      headers: forwardHeaders,
      body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined),
    })
    
    console.log(`[Proxy] Backend response status: ${response.status}`)
    
    // Forward response headers
    for (const [key, value] of response.headers.entries()) {
      // Skip headers that might be invalid for the proxied response
      // content-length: invalid because we might be decompressing
      // content-encoding: invalid because fetch decompresses automatically
      // transfer-encoding: invalid because we let the server handle chunking
      if (!['content-encoding', 'transfer-encoding', 'content-length'].includes(key.toLowerCase())) {
        setResponseHeader(event, key, value)
      }
    }
    
    // Set response status
    setResponseStatus(event, response.status)
    
    // Stream backend response directly to client without parsing
    // This improves performance and avoids memory issues with large JSON responses
    // It also prevents "Content-Length" mismatch errors
    if (response.body) {
      return response.body
    }
    
    // Handle cases with no body
    return null
    
  } catch (error: any) {
    console.error('[Proxy] Error:', error.message)
    console.error('[Proxy] Error type:', error.name)
    
    // Return a proper error response
    setResponseStatus(event, error.statusCode || 500)
    return {
      error: 'Proxy Error',
      message: error.message || 'Failed to connect to backend service',
      details: error.data || null,
      backend: apiBase
    }
  }
})
