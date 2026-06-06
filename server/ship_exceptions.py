"""
Custom exceptions for SHiP framework integration.
Provides structured error handling with specific error codes.
"""

class SHiPTreeGenerationError(Exception):
    """
    Exception raised when SHiP tree generation fails.
    """
    
    def __init__(self, message: str, error_code: str = "SHIP_001"):
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)
    
    def to_dict(self):
        """Convert exception to dictionary for API responses."""
        suggestion = "Please try choosing another tree type."
        if self.error_code == SHIP_TREE_FILEPATH_INVALID:
            suggestion = "This tree type is not compatible with your dataset. Please select a different tree type."
        
        return {
            "error_code": self.error_code,
            "message": self.message,
            "suggestion": suggestion
        }

# Error codes
SHIP_TREE_INVALID = "SHIP_001"
SHIP_TREE_FILEPATH_INVALID = "SHIP_002"