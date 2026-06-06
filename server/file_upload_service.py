import io
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Set, Optional, Any, Union
import chardet
from fastapi import UploadFile, HTTPException
import re
import logging

logger = logging.getLogger(__name__)

class FileUploadService:
    """
    Service for handling file uploads, parsing, and initial data processing.
    Supports CSV, Excel (xlsx, xls), and JSON formats with robust error handling.
    """
    
    # Configuration constants
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB default
    SUPPORTED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.json'}
    CHUNK_SIZE = 8192  # For streaming large files
    
    @classmethod
    async def validate_file(cls, file: UploadFile) -> Dict[str, Any]:
        """
        Validate uploaded file for format, size, and basic content checks.
        """
        # Check file extension
        filename = file.filename.lower() if file.filename else ""
        extension = None
        for ext in cls.SUPPORTED_EXTENSIONS:
            if filename.endswith(ext):
                extension = ext
                break
        
        if not extension:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported formats: {', '.join(cls.SUPPORTED_EXTENSIONS)}"
            )
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > cls.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size of {cls.MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        return {
            "filename": file.filename,
            "size": file_size,
            "extension": extension,
            "mime_type": file.content_type
        }
    
    @classmethod
    async def parse_file(cls, file: UploadFile) -> Dict[str, Any]:
        """
        Parse uploaded file and extract data with metadata.
        Returns structured data with parsing information.
        """
        file_info = await cls.validate_file(file)
        extension = file_info["extension"]
        
        try:
            # Read file content
            content = await file.read()
            await file.seek(0)  # Reset for potential re-reading
            
            if extension == '.csv':
                return await cls._parse_csv(content, file_info)
            elif extension in ['.xlsx', '.xls']:
                return await cls._parse_excel(content, file_info)
            elif extension == '.json':
                return await cls._parse_json(content, file_info)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported extension: {extension}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error parsing file {file.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to parse file: {str(e)}")
    
    @classmethod
    async def _parse_csv(cls, content: bytes, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse CSV content with encoding detection and robust handling."""
        
        # Detect encoding
        encoding_info = chardet.detect(content)
        encoding = encoding_info.get('encoding', 'utf-8')
        confidence = encoding_info.get('confidence', 0)
        
        # Fallback encodings if confidence is low
        fallback_encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        text_content = None
        used_encoding = encoding
        
        for attempt_encoding in [encoding] + fallback_encodings:
            try:
                text_content = content.decode(attempt_encoding)
                used_encoding = attempt_encoding
                break
            except UnicodeDecodeError:
                continue
        
        if text_content is None:
            raise HTTPException(status_code=400, detail="Unable to decode file with any supported encoding")
        
        # Parse CSV using pandas for robustness
        try:
            # Try to detect separator
            separator = cls._detect_csv_separator(text_content)
            
            # First, read CSV without treating first row as headers to detect them properly
            df_no_headers = pd.read_csv(
                io.StringIO(text_content),
                sep=separator,
                header=None,
                engine='python',  # More flexible parsing
                skipinitialspace=True,
                na_values=['', 'null', 'NULL', 'NaN', 'nan', 'N/A', 'n/a', '#N/A', '-'],
                keep_default_na=True
            )
            
            # Detect headers on the raw data
            has_headers = cls._detect_headers(df_no_headers)
            
            if has_headers:
                # Re-read with header=0 to properly extract headers
                df = pd.read_csv(
                    io.StringIO(text_content),
                    sep=separator,
                    header=0,
                    engine='python',
                    skipinitialspace=True,
                    na_values=['', 'null', 'NULL', 'NaN', 'nan', 'N/A', 'n/a', '#N/A', '-'],
                    keep_default_na=True
                )
            else:
                # Use the df_no_headers and generate column names
                df = df_no_headers
                df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]
            
            # Extract data and metadata
            data_array = df.values.tolist()
            headers = df.columns.tolist()
            
            # Validate that when headers are detected, the data doesn't contain header strings
            if has_headers and data_array:
                # Check if first row contains non-numeric strings that look like headers
                first_row = data_array[0] if data_array else []
                header_like_strings = 0
                for cell in first_row:
                    if isinstance(cell, str) and not cls._is_numeric_string(cell):
                        # Check if this string matches any of our detected headers
                        if any(str(cell).lower() == str(header).lower() for header in headers):
                            header_like_strings += 1
                
                # If most of the first row looks like headers, something went wrong - strip it
                if header_like_strings > len(first_row) * 0.5:
                    print(f"[FileUploadService] Warning: First row appears to contain headers despite header detection. Stripping first row.")
                    print(f"[FileUploadService] First row: {first_row[:5]}...")
                    print(f"[FileUploadService] Headers: {headers[:5]}...")
                    data_array = data_array[1:]  # Remove the first row
            
            # Clean NaN values for JSON serialization
            cleaned_data = cls._clean_nan_values(data_array)
            
            # Analyze columns
            column_info = cls._analyze_columns(df)
            
            return {
                "data": cleaned_data,
                "headers": headers,
                "has_headers": has_headers,
                "row_count": int(len(df)),
                "column_count": int(len(df.columns)),
                "column_info": column_info,
                "encoding": used_encoding,
                "encoding_confidence": float(confidence) if confidence else 0.0,
                "separator": separator,
                "file_info": file_info,
                "missing_value_count": int(df.isna().sum().sum()),
                "data_types": df.dtypes.astype(str).to_dict(),
                "header_detection_details": {
                    "method": "backend_pandas",
                    "original_first_row": df.columns.tolist() if has_headers else (df.iloc[0].tolist() if len(df) > 0 else []),
                    "header_indicators_found": has_headers,
                    "final_headers": headers
                }
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")
    
    @classmethod
    async def _parse_excel(cls, content: bytes, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Excel content using pandas."""
        
        try:
            # Read Excel file
            df = pd.read_excel(
                io.BytesIO(content),
                engine='openpyxl' if file_info["extension"] == '.xlsx' else 'xlrd',
                na_values=['', 'null', 'NULL', 'NaN', 'nan', 'N/A', 'n/a', '#N/A', '-'],
                keep_default_na=True
            )
            
            # Detect headers (Excel files typically have headers)
            has_headers = True
            if df.empty or len(df) < 2:
                has_headers = False
            
            # Extract data and metadata
            data_array = df.values.tolist()
            headers = df.columns.tolist()
            
            # Clean NaN values for JSON serialization
            cleaned_data = cls._clean_nan_values(data_array)
            
            # Analyze columns
            column_info = cls._analyze_columns(df)
            
            return {
                "data": cleaned_data,
                "headers": headers,
                "has_headers": has_headers,
                "row_count": int(len(df)),
                "column_count": int(len(df.columns)),
                "column_info": column_info,
                "file_info": file_info,
                "missing_value_count": int(df.isna().sum().sum()),
                "data_types": df.dtypes.astype(str).to_dict()
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Excel parsing error: {str(e)}")
    
    @classmethod
    async def _parse_json(cls, content: bytes, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON content."""
        
        try:
            # Decode JSON
            text_content = content.decode('utf-8')
            json_data = json.loads(text_content)
            
            # Validate JSON structure (should be array of arrays or array of objects)
            if not isinstance(json_data, list):
                raise HTTPException(status_code=400, detail="JSON must be an array")
            
            if len(json_data) == 0:
                return {
                    "data": [],
                    "headers": [],
                    "has_headers": False,
                    "row_count": 0,
                    "column_count": 0,
                    "column_info": [],
                    "file_info": file_info,
                    "missing_value_count": 0,
                    "data_types": {}
                }
            
            # Handle array of objects (convert to array of arrays)
            if isinstance(json_data[0], dict):
                headers = list(json_data[0].keys())
                data_array = []
                for row in json_data:
                    if not isinstance(row, dict):
                        raise HTTPException(status_code=400, detail="Inconsistent JSON structure")
                    data_array.append([row.get(header, None) for header in headers])
                has_headers = True
            
            # Handle array of arrays
            elif isinstance(json_data[0], list):
                data_array = json_data
                if len(data_array) > 0:
                    headers = [f"Column_{i+1}" for i in range(len(data_array[0]))]
                else:
                    headers = []
                has_headers = False
            
            else:
                raise HTTPException(status_code=400, detail="JSON must contain arrays or objects")
            
            # Clean NaN values for JSON serialization
            cleaned_data = cls._clean_nan_values(data_array)
            
            # Convert to DataFrame for analysis
            if data_array:
                df = pd.DataFrame(data_array, columns=headers)
                column_info = cls._analyze_columns(df)
                missing_count = int(df.isna().sum().sum())
                data_types = df.dtypes.astype(str).to_dict()
            else:
                column_info = []
                missing_count = 0
                data_types = {}
            
            return {
                "data": cleaned_data,
                "headers": headers,
                "has_headers": has_headers,
                "row_count": int(len(data_array)),
                "column_count": int(len(headers)),
                "column_info": column_info,
                "file_info": file_info,
                "missing_value_count": int(missing_count),
                "data_types": data_types
            }
            
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"JSON parsing error: {str(e)}")
    
    @classmethod
    def _detect_csv_separator(cls, content: str) -> str:
        """Detect CSV separator using pandas sniffer and heuristics."""
        
        # Try pandas' separator detection first
        try:
            sample = '\n'.join(content.split('\n')[:10])  # First 10 lines
            df = pd.read_csv(io.StringIO(sample), sep=None, engine='python', nrows=5)
            return df.sep if hasattr(df, 'sep') else ','
        except:
            pass
        
        # Fallback to heuristic detection
        sample_lines = content.split('\n')[:10]
        separators = [',', ';', '\t', '|']
        separator_counts = {}
        
        for sep in separators:
            counts = []
            for line in sample_lines:
                if line.strip():
                    counts.append(line.count(sep))
            
            if counts:
                # Check for consistency
                unique_counts = set(counts)
                if len(unique_counts) == 1 and counts[0] > 0:
                    separator_counts[sep] = counts[0]
        
        if separator_counts:
            return max(separator_counts.items(), key=lambda x: x[1])[0]
        
        return ','  # Default fallback
    
    @classmethod
    def _detect_headers(cls, df: pd.DataFrame) -> bool:
        """Detect if first row contains headers."""
        
        if len(df) < 2:
            return False
        
        # Get first two rows
        first_row = df.iloc[0]
        second_row = df.iloc[1]
        
        header_indicators = 0
        total_columns = len(df.columns)
        
        for i in range(total_columns):
            first_val = first_row.iloc[i]
            second_val = second_row.iloc[i]
            
            # Check if first row value is string and second is numeric
            if (isinstance(first_val, str) and 
                not cls._is_numeric_string(first_val) and
                cls._is_numeric_string(str(second_val))):
                header_indicators += 1
            
            # Check for common header patterns
            if isinstance(first_val, str):
                first_val_lower = first_val.lower()
                # Expanded header keywords including label-related terms
                header_keywords = [
                    'id', 'name', 'value', 'count', 'feature', 'column', 'field',
                    'label', 'target', 'class', 'category', 'group', 'cluster',
                    'type', 'status', 'description', 'title', 'key', 'index'
                ]
                if any(keyword in first_val_lower for keyword in header_keywords):
                    header_indicators += 1
                
                # Check for header-like patterns (camelCase, snake_case, etc.)
                if ('_' in first_val or first_val != first_val.lower() or 
                    any(c.isupper() for c in first_val[1:])):
                    header_indicators += 0.5
                    
                # Check if first row has fewer numeric values than second row
                first_is_numeric = cls._is_numeric_string(str(first_val))
                second_is_numeric = cls._is_numeric_string(str(second_val))
                if not first_is_numeric and second_is_numeric:
                    header_indicators += 0.5
        
        # More lenient threshold for header detection
        header_ratio = header_indicators / total_columns
        return header_ratio > 0.3  # Reduced from 0.5 to catch more header cases
    
    @classmethod
    def _is_numeric_string(cls, value: str) -> bool:
        """Check if string represents a number."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @classmethod
    def _analyze_columns(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze each column to determine data types and characteristics."""
        
        column_info = []
        
        for col_name in df.columns:
            series = df[col_name]
            non_null_series = series.dropna()
            
            if len(non_null_series) == 0:
                column_info.append({
                    "name": str(col_name),
                    "data_type": "empty",
                    "non_null_count": 0,
                    "null_count": int(len(series)),
                    "unique_count": 0,
                    "sample_values": [],
                    "is_categorical": False,
                    "is_numeric": False,
                    "unique_ratio": 0.0
                })
                continue
            
            # Determine data type
            data_type = "mixed"
            is_numeric = False
            is_categorical = False
            
            # Check if numeric
            numeric_count = 0
            for val in non_null_series:
                if pd.api.types.is_numeric_dtype(type(val)) or cls._is_numeric_string(str(val)):
                    numeric_count += 1
            
            numeric_ratio = numeric_count / len(non_null_series)
            
            if numeric_ratio > 0.9:
                is_numeric = True
                # Check if integer
                try:
                    numeric_series = pd.to_numeric(non_null_series, errors='coerce')
                    if numeric_series.notna().all():
                        if (numeric_series % 1 == 0).all():
                            data_type = "integer"
                        else:
                            data_type = "numeric"
                    else:
                        data_type = "mixed"
                except:
                    data_type = "mixed"
            elif numeric_ratio < 0.1:
                # Check if categorical
                unique_ratio = len(non_null_series.unique()) / len(non_null_series)
                if unique_ratio < 0.5:  # Less than 50% unique values
                    is_categorical = True
                    data_type = "categorical"
                else:
                    # Check if it's still categorical based on data patterns
                    # Even if high unique ratio, short strings or common patterns might be categorical
                    avg_length = sum(len(str(val)) for val in non_null_series) / len(non_null_series)
                    if avg_length < 20 and unique_ratio < 0.8:  # Short strings, reasonably unique
                        is_categorical = True
                        data_type = "categorical"
                    else:
                        data_type = "text"
            else:
                # Mixed numeric/non-numeric data - likely categorical
                is_categorical = True
                data_type = "categorical"
            
            # Get sample values
            sample_values = non_null_series.head(5).tolist()
            
            column_info.append({
                "name": str(col_name),
                "data_type": str(data_type),
                "non_null_count": int(len(non_null_series)),
                "null_count": int(series.isna().sum()),
                "unique_count": int(len(non_null_series.unique())),
                "sample_values": [str(val)[:50] for val in sample_values],  # Truncate long values
                "is_categorical": bool(is_categorical),
                "is_numeric": bool(is_numeric),
                "unique_ratio": float(len(non_null_series.unique()) / len(non_null_series) if len(non_null_series) > 0 else 0)
            })
        
        return column_info
    
    @classmethod
    async def get_preview(cls, parsed_data: Dict[str, Any], num_rows: int = 10) -> Dict[str, Any]:
        """Get a preview of the parsed data."""
        
        data = parsed_data["data"]
        headers = parsed_data["headers"]
        
        preview_data = data[:num_rows] if len(data) > num_rows else data
        
        return {
            "headers": headers,
            "data": preview_data,
            "total_rows": len(data),
            "preview_rows": len(preview_data),
            "column_info": parsed_data["column_info"],
            "has_headers": parsed_data["has_headers"]
        }

    @staticmethod
    def _clean_nan_values(data: Any) -> Any:
        """
        Recursively replace NaN values with None for JSON serialization.
        """
        if isinstance(data, list):
            return [FileUploadService._clean_nan_values(item) for item in data]
        elif isinstance(data, dict):
            return {key: FileUploadService._clean_nan_values(value) for key, value in data.items()}
        elif isinstance(data, (int, float)) and (pd.isna(data) or np.isnan(data)):
            return None
        elif isinstance(data, np.ndarray):
            # Convert numpy array to list and clean NaN values
            array_list = data.tolist()
            return FileUploadService._clean_nan_values(array_list)
        elif pd.isna(data):
            return None
        else:
            return data