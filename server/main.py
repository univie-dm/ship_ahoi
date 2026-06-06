#!/usr/bin/env python3
"""
Main entry point for the Clustering Analysis Backend API
"""

import uvicorn
from clustering_api import app

if __name__ == "__main__":
    print("Starting Clustering Analysis Backend API...")
    print("K-Selection Analysis endpoints:")
    print("  POST /api/k-selection/analyze")
    print("  POST /api/k-selection/cluster-visualization")
    print("Regular clustering endpoints:")
    print("  POST /api/cluster/regular")
    print("  POST /api/cluster/colored")
    print("  GET /api/cluster/options")
    print("\nServer will be available at: http://localhost:8000")
    print("API documentation will be available at: http://localhost:8000/docs")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["./"]
    ) 