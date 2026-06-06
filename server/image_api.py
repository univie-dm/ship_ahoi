"""
API endpoint for serving image data for dataset points.
Supports image datasets like digits, faces, and object recognition datasets.
"""
import io
import base64
import numpy as np
from PIL import Image
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from typing import Optional, Tuple, Dict, Any
import logging

from .toy_dataset_service import ToyDatasetService
from sklearn.datasets import load_digits, fetch_olivetti_faces

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache for dataset metadata to avoid reloading
_dataset_cache: Dict[str, Dict[str, Any]] = {}

def get_image_dimensions(dataset_name: str) -> Tuple[int, int]:
    """Get the expected image dimensions for a dataset."""
    dimensions = {
        'digits_full': (8, 8),
        'digits_small': (8, 8),
        'olivetti_faces': (64, 64),
        'lfw_faces': (62, 47),  # Default LFW size (grayscale)
        'coil20': (32, 32),     # COIL20 typically 32x32
        'coil100': (128, 128),  # COIL100 typically 128x128
        'mnist_full': (28, 28),
        'fashion_mnist': (28, 28),
        'sign_language_digits': (64, 64),
        'dataset_2': (28, 28),
    }
    return dimensions.get(dataset_name, (8, 8))  # Default fallback

def normalize_image_data(image_data: np.ndarray, dataset_name: str) -> np.ndarray:
    """Normalize image data to 0-255 range and proper shape."""
    # Handle different data ranges
    if image_data.max() <= 1.0:
        # Data is in 0-1 range
        image_data = (image_data * 255).astype(np.uint8)
    elif image_data.max() <= 16.0:
        # Data might be in 0-16 range (common for digits)
        image_data = (image_data * 255 / image_data.max()).astype(np.uint8)
    else:
        # Data is likely already in 0-255 range
        image_data = np.clip(image_data, 0, 255).astype(np.uint8)
    
    return image_data

def create_image_from_data(image_data: np.ndarray, dataset_name: str) -> Image.Image:
    """Create a PIL Image from dataset point data."""
    height, width = get_image_dimensions(dataset_name)
    
    # Reshape data to image dimensions
    if len(image_data.shape) == 1:
        # Flatten data, need to reshape
        expected_size = height * width
        if len(image_data) >= expected_size:
            image_data = image_data[:expected_size].reshape(height, width)
        else:
            # Pad with zeros if data is smaller than expected
            padded_data = np.zeros(expected_size)
            padded_data[:len(image_data)] = image_data
            image_data = padded_data.reshape(height, width)
    elif len(image_data.shape) == 2:
        # Already 2D, might need resizing
        if image_data.shape != (height, width):
            # Try to reshape if sizes are compatible
            if image_data.shape[0] * image_data.shape[1] == height * width:
                image_data = image_data.reshape(height, width)
    
    # Normalize to 0-255 range
    image_data = normalize_image_data(image_data, dataset_name)
    
    # Create PIL Image
    if len(image_data.shape) == 2:
        # Grayscale image
        img = Image.fromarray(image_data, mode='L')
    else:
        # Color image (should have 3 channels)
        img = Image.fromarray(image_data, mode='RGB')
    
    # Scale up small images for better visibility
    if max(img.size) < 64:
        scale_factor = 64 // max(img.size)
        new_size = (img.width * scale_factor, img.height * scale_factor)
        img = img.resize(new_size, Image.NEAREST)  # Use nearest neighbor for pixel art
    
    return img

def load_dataset_if_needed(dataset_name: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load dataset data if not already cached."""
    global _dataset_cache
    
    if dataset_name in _dataset_cache:
        cached = _dataset_cache[dataset_name]
        return cached['data'], cached['target']
    
    logger.info(f"Loading dataset {dataset_name} for image serving")
    
    try:
        if dataset_name == 'digits_small':
            sklearn_data = load_digits()
            X, y = sklearn_data.data, sklearn_data.target
        elif dataset_name == 'digits_full':
            # Use ToyDatasetService to get the raw UCI digits dataset (5620 samples) without standardization
            X, y = ToyDatasetService._load_digits_full()
        elif dataset_name == 'olivetti_faces':
            sklearn_data = fetch_olivetti_faces()
            X, y = sklearn_data.data, sklearn_data.target
        elif dataset_name == 'lfw_faces':
            X, y = ToyDatasetService._load_lfw_faces()
        elif dataset_name == 'fashion_mnist':
            X, y = ToyDatasetService._load_fashion_mnist()
        elif dataset_name == 'sign_language_digits':
            X, y = ToyDatasetService._load_sign_language_digits()
        elif dataset_name == 'dataset_2':
            X, y = ToyDatasetService._load_fashion_mnist()
            X, y = X[:5000], y[:5000]
        else:
            # Use ToyDatasetService for other datasets
            X, y = ToyDatasetService.generate_dataset(dataset_name, n_samples=10000)
        
        # Cache the dataset
        _dataset_cache[dataset_name] = {
            'data': X,
            'target': y,
            'loaded_at': import_time.time()
        }
        
        logger.info(f"Successfully loaded {dataset_name}: {X.shape[0]} samples")
        return X, y
        
    except Exception as e:
        logger.error(f"Failed to load dataset {dataset_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {e}")

@router.get("/dataset-image/{dataset_name}/{point_index}")
async def get_dataset_image(dataset_name: str, point_index: int):
    """
    Get image data for a specific point in an image dataset.
    
    Args:
        dataset_name: Name of the dataset (e.g., 'digits_full', 'olivetti_faces')
        point_index: Index of the data point to visualize as an image
    
    Returns:
        PNG image data as a streaming response
    """
    # Validate dataset name
    image_datasets = [
        'digits_full', 'digits_small', 'olivetti_faces', 'lfw_faces',
        'coil20', 'coil100', 'mnist_full', 'fashion_mnist', 'sign_language_digits',
        'dataset_2'
    ]
    
    if dataset_name not in image_datasets:
        raise HTTPException(
            status_code=400, 
            detail=f"Dataset {dataset_name} does not support image visualization"
        )
    
    try:
        # Load dataset
        X, y = load_dataset_if_needed(dataset_name)
        
        # Validate point index
        if point_index < 0 or point_index >= len(X):
            raise HTTPException(
                status_code=404,
                detail=f"Point index {point_index} out of range (0-{len(X)-1})"
            )
        
        # Get image data for the point
        image_data = X[point_index]
        
        # Create PIL Image
        img = create_image_from_data(image_data, dataset_name)
        
        # Convert to PNG bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(img_buffer.read()),
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Content-Disposition": f"inline; filename=point_{point_index}.png"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating image for {dataset_name} point {point_index}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")

@router.get("/dataset-image-info/{dataset_name}")
async def get_dataset_image_info(dataset_name: str):
    """
    Get information about image capabilities for a dataset.
    
    Returns metadata about whether the dataset supports images and dimensions.
    """
    image_datasets = {
        'digits_full': {
            'supports_images': True,
            'dimensions': (8, 8),
            'type': 'grayscale',
            'description': 'Handwritten digits (8x8 pixels)'
        },
        'digits_small': {
            'supports_images': True,
            'dimensions': (8, 8),
            'type': 'grayscale',
            'description': 'Handwritten digits (8x8 pixels)'
        },
        'olivetti_faces': {
            'supports_images': True,
            'dimensions': (64, 64),
            'type': 'grayscale',
            'description': 'Face images (64x64 pixels)'
        },
        'lfw_faces': {
            'supports_images': True,
            'dimensions': (62, 47),
            'type': 'grayscale',
            'description': 'Labeled Faces in the Wild (aligned)'
        },
        'coil20': {
            'supports_images': True,
            'dimensions': (32, 32),
            'type': 'grayscale',
            'description': 'COIL20 object recognition'
        },
        'coil100': {
            'supports_images': True,
            'dimensions': (128, 128),
            'type': 'color',
            'description': 'COIL100 object recognition'
        },
        'mnist_full': {
            'supports_images': True,
            'dimensions': (28, 28),
            'type': 'grayscale',
            'description': 'MNIST handwritten digits'
        },
        'fashion_mnist': {
            'supports_images': True,
            'dimensions': (28, 28),
            'type': 'grayscale',
            'description': 'Fashion-MNIST clothing items'
        },
        'sign_language_digits': {
            'supports_images': True,
            'dimensions': (64, 64),
            'type': 'grayscale',
            'description': 'American Sign Language digits (gesture photos)'
        }
    }
    
    if dataset_name not in image_datasets:
        return {
            'supports_images': False,
            'reason': f'Dataset {dataset_name} does not contain image data'
        }
    
    return image_datasets[dataset_name]

# Import time for caching timestamps
import time as import_time
