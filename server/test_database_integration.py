#!/usr/bin/env python3
"""
Test script for database integration
Tests basic database operations and connectivity
"""

import asyncio
import sys
import os
import numpy as np
from datetime import datetime

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from redis_service import RedisService
from models import (
    DatasetCreate, ClusteringResultCreate, 
    SHiPObjectCreate, DimensionalityReductionResultCreate,
    KSelectionCacheCreate, ClusteringStatus, DRMethod, DRStatus
)

async def test_database_connection():
    """Test basic database connection"""
    print("=" * 50)
    print("Testing Database Connection")
    print("=" * 50)
    
    db = DatabaseService()
    
    try:
        await db.connect()
        print("✓ Database connection successful")
        
        health = await db.health_check()
        print(f"✓ Health check: {health['status']}")
        print(f"  Database: {health.get('database', 'N/A')}")
        print(f"  Collections: {health.get('collections', [])}")
        
        await db.disconnect()
        print("✓ Database disconnection successful")
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    return True

async def test_dataset_operations():
    """Test dataset CRUD operations"""
    print("\n" + "=" * 50)
    print("Testing Dataset Operations")
    print("=" * 50)
    
    db = DatabaseService()
    await db.connect()
    
    try:
        # Create dataset
        dataset = DatasetCreate(
            filename="test_dataset.csv",
            original_filename="test_dataset.csv",
            content_type="text/csv",
            file_size=1024,
            data_hash="test_hash_123",
            processed_data={
                "headers": ["col1", "col2", "col3"],
                "data": [[1, 2, 3], [4, 5, 6]],
                "metadata": {"rows": 2, "columns": 3}
            }
        )
        
        created_dataset = await db.create_dataset(dataset)
        print(f"✓ Created dataset: {created_dataset.filename}")
        
        # Get dataset
        retrieved_dataset = await db.get_dataset(created_dataset.id)
        print(f"✓ Retrieved dataset: {retrieved_dataset.filename}")
        
        # List datasets
        datasets = await db.list_datasets(limit=10)
        print(f"✓ Listed {len(datasets)} datasets")
        
        # Update dataset
        from models import DatasetUpdate
        update_data = DatasetUpdate(filename="updated_test_dataset.csv")
        updated_dataset = await db.update_dataset(created_dataset.id, update_data)
        print(f"✓ Updated dataset filename to: {updated_dataset.filename}")
        
        # Delete dataset
        deleted = await db.delete_dataset(created_dataset.id)
        print(f"✓ Deleted dataset: {deleted}")
        
    except Exception as e:
        print(f"✗ Dataset operations failed: {e}")
        return False
    finally:
        await db.disconnect()
    
    return True

async def test_clustering_operations():
    """Test clustering result operations"""
    print("\n" + "=" * 50)
    print("Testing Clustering Operations")
    print("=" * 50)
    
    db = DatabaseService()
    await db.connect()
    
    try:
        # Create clustering result
        clustering_result = ClusteringResultCreate(
            operation_id="test_op_123",
            cluster_id="test_cluster_456",
            dataset_id="test_dataset_789",
            parameters={"k": 3, "method": "hierarchical"},
            result={
                "tree": {"nodes": [], "links": []},
                "clusters": [1, 2, 1, 3, 2],
                "metrics": {"silhouette": 0.75}
            },
            data={
                "processed_data": [[1, 2], [3, 4], [5, 6]],
                "labels": [1, 2, 1]
            },
            status=ClusteringStatus.COMPLETED
        )
        
        created_result = await db.create_clustering_result(clustering_result)
        print(f"✓ Created clustering result: {created_result.operation_id}")
        
        # Get clustering result
        retrieved_result = await db.get_clustering_result(created_result.id)
        print(f"✓ Retrieved clustering result: {retrieved_result.operation_id}")
        
        # Get by operation ID
        result_by_op = await db.get_clustering_result_by_operation_id(created_result.operation_id)
        print(f"✓ Retrieved by operation ID: {result_by_op.operation_id}")
        
        # List clustering results
        results = await db.list_clustering_results(limit=10)
        print(f"✓ Listed {len(results)} clustering results")
        
    except Exception as e:
        print(f"✗ Clustering operations failed: {e}")
        return False
    finally:
        await db.disconnect()
    
    return True

async def test_ship_object_operations():
    """Test SHiP object operations"""
    print("\n" + "=" * 50)
    print("Testing SHiP Object Operations")
    print("=" * 50)
    
    db = DatabaseService()
    await db.connect()
    
    try:
        # Create SHiP object
        ship_obj = SHiPObjectCreate(
            data_hash="test_ship_hash_123",
            tree_type="DCTree",
            config={"min_points": 2, "min_cluster_size": 5},
            data_shape=[100, 10]
        )
        
        created_ship = await db.create_ship_object(ship_obj)
        print(f"✓ Created SHiP object: {created_ship.data_hash[:8]}...")
        
        # Get SHiP object
        retrieved_ship = await db.get_ship_object(
            created_ship.data_hash,
            created_ship.tree_type,
            created_ship.config
        )
        print(f"✓ Retrieved SHiP object: {retrieved_ship.data_hash[:8]}...")
        
        # Test cleanup
        cleaned_up = await db.cleanup_old_ship_objects(days_old=0)  # Clean up everything
        print(f"✓ Cleaned up {cleaned_up} old SHiP objects")
        
    except Exception as e:
        print(f"✗ SHiP object operations failed: {e}")
        return False
    finally:
        await db.disconnect()
    
    return True

async def test_dr_operations():
    """Test dimensionality reduction operations"""
    print("\n" + "=" * 50)
    print("Testing Dimensionality Reduction Operations")
    print("=" * 50)
    
    db = DatabaseService()
    await db.connect()
    
    try:
        # Create DR result
        dr_result = DimensionalityReductionResultCreate(
            cluster_id="test_cluster_dr_123",
            method=DRMethod.UMAP,
            parameters={"n_neighbors": 15, "min_dist": 0.1},
            result={
                "embedding": [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
                "explained_variance": 0.85
            },
            status=DRStatus.COMPLETED
        )
        
        created_dr = await db.create_dr_result(dr_result)
        print(f"✓ Created DR result: {created_dr.cluster_id}")
        
        # Get DR result
        retrieved_dr = await db.get_dr_result(created_dr.cluster_id, created_dr.method)
        print(f"✓ Retrieved DR result: {retrieved_dr.method}")
        
    except Exception as e:
        print(f"✗ DR operations failed: {e}")
        return False
    finally:
        await db.disconnect()
    
    return True

async def test_k_selection_cache():
    """Test K-selection cache operations"""
    print("\n" + "=" * 50)
    print("Testing K-Selection Cache Operations")
    print("=" * 50)
    
    db = DatabaseService()
    await db.connect()
    
    try:
        # Create cache entry
        cache_entry = KSelectionCacheCreate(
            dataset_id="test_dataset_cache_123",
            cache_data={
                "k_values": [2, 3, 4, 5],
                "metrics": {"silhouette": [0.5, 0.7, 0.6, 0.4]},
                "recommendations": {"optimal_k": 3}
            }
        )
        
        created_cache = await db.create_k_selection_cache(cache_entry)
        print(f"✓ Created K-selection cache: {created_cache.dataset_id}")
        
        # Get cache entry
        retrieved_cache = await db.get_k_selection_cache(created_cache.dataset_id)
        print(f"✓ Retrieved K-selection cache: {retrieved_cache.dataset_id}")
        
        # Test cleanup
        cleaned_up = await db.cleanup_expired_cache()
        print(f"✓ Cleaned up {cleaned_up} expired cache entries")
        
    except Exception as e:
        print(f"✗ K-selection cache operations failed: {e}")
        return False
    finally:
        await db.disconnect()
    
    return True

async def main():
    """Run all database tests"""
    print("SHiP Clustering Database Integration Test")
    print("=" * 50)
    
    tests = [
        test_database_connection,
        test_dataset_operations,
        test_clustering_operations,
        test_ship_object_operations,
        test_dr_operations,
        test_k_selection_cache
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("Test Results")
    print("=" * 50)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))