import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Set, Optional, Any, Union
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder, OneHotEncoder
from fastapi import HTTPException
import logging
from .cluster_params import DataProcessingConfig

logger = logging.getLogger(__name__)

class DataProcessingService:
    """
    Service for data preprocessing including missing value handling,
    normalization, categorical encoding, and feature selection.
    """
    
    @classmethod
    def _is_categorical_column(cls, column: pd.Series) -> bool:
        """
        Determine if a column should be treated as categorical.
        
        Args:
            column: Pandas Series to check
            
        Returns:
            True if column should be treated as categorical
        """
        # Check if column contains object/string data
        if column.dtype == 'object':
            return True
        
        # Check if column has non-numeric values
        try:
            pd.to_numeric(column, errors='raise')
            return False
        except (ValueError, TypeError):
            return True
    
    @classmethod
    def _is_numeric_column(cls, column: pd.Series) -> bool:
        """
        Determine if a column is purely numeric.
        
        Args:
            column: Pandas Series to check
            
        Returns:
            True if column is purely numeric
        """
        try:
            pd.to_numeric(column, errors='raise')
            return True
        except (ValueError, TypeError):
            return False
    
    @classmethod
    def process_data(cls, 
                     raw_data: List[List[Any]], 
                     headers: List[str],
                     processing_config: DataProcessingConfig,
                     ground_truth_column: int = None) -> Dict[str, Any]:
        """
        Process raw data according to configuration.
        
        Args:
            raw_data: Raw data as list of lists
            headers: Column headers
            processing_config: DataProcessingConfig object
            
        Returns:
            Dictionary with processed data and metadata
        """
        try:
            # Convert to DataFrame for easier processing
            df = pd.DataFrame(raw_data, columns=headers)
            
            # Extract ground truth labels before any processing
            ground_truth_labels = None
            if ground_truth_column is not None and ground_truth_column < len(headers):
                try:
                    ground_truth_labels = df.iloc[:, ground_truth_column].tolist()
                    print(f"[DataProcessingService] Extracted ground truth labels from column {ground_truth_column} ({headers[ground_truth_column]})")
                except (ValueError, IndexError) as e:
                    print(f"[DataProcessingService] Warning: Could not extract ground truth labels from column {ground_truth_column}: {e}")
            
            # Extract configuration from Pydantic model
            missing_strategy = processing_config.missing_value_strategy
            normalization = processing_config.normalization
            categorical_encoding = processing_config.categorical_encoding
            feature_columns = processing_config.feature_columns or list(range(len(headers)))
            ignored_columns = processing_config.ignored_columns or []
            column_configs = processing_config.columns or []
            
            # Create column configuration mapping
            column_config_map = {}
            if column_configs:
                for config in column_configs:
                    if hasattr(config, 'index') and config.index < len(headers):
                        column_config_map[config.index] = config
                    elif isinstance(config, dict) and 'index' in config and config['index'] < len(headers):
                        column_config_map[config['index']] = config
            
            # Step 1: Handle missing values
            df_processed = cls._handle_missing_values(df, missing_strategy)
            
            # Step 2: Select feature columns only
            feature_df = cls._select_feature_columns(df_processed, feature_columns, ignored_columns)
            feature_headers = [headers[i] for i in feature_columns if i not in ignored_columns]
            
            # Step 3: Process categorical variables
            categorical_info = {}
            if categorical_encoding != 'none':
                # Create a mapping from new feature column indices to original column indices
                feature_to_original_map = {}
                for new_idx, original_idx in enumerate([col for col in feature_columns if col not in ignored_columns]):
                    feature_to_original_map[new_idx] = original_idx
                
                feature_df, categorical_info = cls._handle_categorical_variables(
                    feature_df, feature_headers, categorical_encoding, column_config_map, feature_to_original_map
                )
                # Update feature headers to match processed columns
                feature_headers = feature_df.columns.tolist()
            
            # Step 4: Apply normalization
            normalization_info = {}
            if normalization != 'none':
                # Create column config mapping for the selected feature columns
                feature_config_map = {}
                for new_idx, original_idx in enumerate([col for col in feature_columns if col not in ignored_columns]):
                    if original_idx in column_config_map:
                        feature_config_map[new_idx] = column_config_map[original_idx]
                
                feature_df, normalization_info = cls._apply_normalization(
                    feature_df, normalization, feature_config_map, categorical_info
                )
            
            # Step 5: Final data validation and conversion
            processed_data = cls._finalize_data(feature_df)
            
            return {
                "data": processed_data,
                "headers": feature_headers,
                "row_count": int(len(processed_data)),
                "column_count": int(len(feature_df.columns)),
                "ground_truth_labels": ground_truth_labels,
                "processing_info": {
                    "missing_strategy": str(missing_strategy),
                    "normalization": str(normalization),
                    "categorical_encoding": str(categorical_encoding),
                    "original_shape": [int(x) for x in df.shape],
                    "processed_shape": [int(x) for x in feature_df.shape],
                    "removed_rows": int(len(df) - len(feature_df)),
                    "categorical_info": categorical_info,
                    "normalization_info": normalization_info
                },
                "feature_columns": [int(x) for x in feature_columns],
                "ignored_columns": [int(x) for x in ignored_columns]
            }
            
        except Exception as e:
            logger.error(f"Data processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Data processing failed: {str(e)}")
    
    @classmethod
    def _handle_missing_values(cls, df: pd.DataFrame, strategy: str) -> pd.DataFrame:
        """Handle missing values according to strategy."""
        
        if strategy == 'keep':
            return df
        
        elif strategy == 'remove':
            return df.dropna()
        
        elif strategy == 'fill_mean':
            df_filled = df.copy()
            numeric_columns = df_filled.select_dtypes(include=[np.number]).columns
            for col in numeric_columns:
                df_filled[col] = df_filled[col].fillna(df_filled[col].mean())
            # For non-numeric columns, use mode
            non_numeric_columns = df_filled.select_dtypes(exclude=[np.number]).columns
            for col in non_numeric_columns:
                mode_val = df_filled[col].mode()
                if not mode_val.empty:
                    df_filled[col] = df_filled[col].fillna(mode_val[0])
            return df_filled
        
        elif strategy == 'fill_median':
            df_filled = df.copy()
            numeric_columns = df_filled.select_dtypes(include=[np.number]).columns
            for col in numeric_columns:
                df_filled[col] = df_filled[col].fillna(df_filled[col].median())
            # For non-numeric columns, use mode
            non_numeric_columns = df_filled.select_dtypes(exclude=[np.number]).columns
            for col in non_numeric_columns:
                mode_val = df_filled[col].mode()
                if not mode_val.empty:
                    df_filled[col] = df_filled[col].fillna(mode_val[0])
            return df_filled
        
        elif strategy == 'fill_zero':
            return df.fillna(0)
        
        elif strategy == 'fill_mode':
            df_filled = df.copy()
            for col in df_filled.columns:
                mode_val = df_filled[col].mode()
                if not mode_val.empty:
                    df_filled[col] = df_filled[col].fillna(mode_val[0])
            return df_filled
        
        else:
            logger.warning(f"Unknown missing value strategy: {strategy}. Using 'keep'.")
            return df
    
    @classmethod
    def _select_feature_columns(cls, df: pd.DataFrame, feature_columns: List[int], ignored_columns: List[int]) -> pd.DataFrame:
        """Select only the feature columns, excluding ignored columns."""
        
        # Get valid feature columns (not in ignored list)
        valid_feature_columns = [col for col in feature_columns if col not in ignored_columns and col < len(df.columns)]
        
        if not valid_feature_columns:
            raise HTTPException(status_code=400, detail="No valid feature columns selected")
        
        # Select columns by index
        selected_df = df.iloc[:, valid_feature_columns].copy()
        
        return selected_df
    
    @classmethod
    def _handle_categorical_variables(cls, 
                                    df: pd.DataFrame, 
                                    headers: List[str],
                                    encoding_method: str,
                                    column_config_map: Dict[int, Dict],
                                    feature_to_original_map: Dict[int, int] = None) -> Tuple[pd.DataFrame, Dict]:
        """Handle categorical variables with specified encoding method."""
        
        categorical_info = {}
        df_encoded = df.copy()
        
        if encoding_method == 'none' or encoding_method == 'label':
            # Label encoding for categorical columns in the feature set
            for i, col in enumerate(df.columns):
                # Map the current column to original column index using the provided mapping
                if feature_to_original_map and i in feature_to_original_map:
                    original_col_idx = feature_to_original_map[i]
                else:
                    # Fallback to old method if mapping not provided
                    original_col_idx = headers.index(col) if col in headers else i
                
                config = column_config_map.get(original_col_idx)
                
                # Check if column should be treated as categorical
                is_categorical = False
                
                if config:
                    if hasattr(config, 'is_categorical'):
                        is_categorical = config.is_categorical
                    elif isinstance(config, dict):
                        is_categorical = config.get('is_categorical', False)
                else:
                    # Fallback: auto-detect categorical columns when config is missing
                    is_categorical = cls._is_categorical_column(df[col])
                
                # Since we're only working with feature columns at this point (filtered in _select_feature_columns),
                # encode any categorical column regardless of its usage configuration
                # This fixes the issue where categorical columns marked as 'label' usage were not being encoded
                if is_categorical and (df[col].dtype == 'object' or not cls._is_numeric_column(df[col])):
                    # Apply label encoding
                    encoder = LabelEncoder()
                    non_null_mask = df[col].notna()
                    
                    if non_null_mask.any():
                        encoded_values = encoder.fit_transform(df[col][non_null_mask])
                        df_encoded.loc[non_null_mask, col] = encoded_values
                        
                        # Create mapping dictionary for each unique value
                        mapping_dict = {}
                        for original_value, encoded_value in zip(encoder.classes_, range(len(encoder.classes_))):
                            mapping_dict[str(original_value)] = int(encoded_value)
                        
                        categorical_info[col] = {
                            "encoding_method": "label",
                            "classes": encoder.classes_.tolist(),
                            "encoded_count": len(encoded_values),
                            "mapping": mapping_dict,
                            "reverse_mapping": {int(v): str(k) for k, v in mapping_dict.items()}
                        }
        
        elif encoding_method == 'onehot':
            # One-hot encoding for categorical columns in the feature set
            columns_to_encode = []
            
            for i, col in enumerate(df.columns):
                # Map the current column to original column index using the provided mapping
                if feature_to_original_map and i in feature_to_original_map:
                    original_col_idx = feature_to_original_map[i]
                else:
                    # Fallback to old method if mapping not provided
                    original_col_idx = headers.index(col) if col in headers else i
                
                config = column_config_map.get(original_col_idx)
                
                # Check if column should be treated as categorical
                is_categorical = False
                
                if config:
                    if hasattr(config, 'is_categorical'):
                        is_categorical = config.is_categorical
                    elif isinstance(config, dict):
                        is_categorical = config.get('is_categorical', False)
                else:
                    # Fallback: auto-detect categorical columns when config is missing
                    is_categorical = cls._is_categorical_column(df[col])
                
                # Since we're only working with feature columns at this point (filtered in _select_feature_columns),
                # encode any categorical column regardless of its usage configuration
                if is_categorical and (df[col].dtype == 'object' or not cls._is_numeric_column(df[col])):
                    columns_to_encode.append(col)
            
            if columns_to_encode:
                # Apply one-hot encoding
                df_encoded = pd.get_dummies(df, columns=columns_to_encode, prefix=columns_to_encode, dummy_na=True)
                
                for col in columns_to_encode:
                    # Find all columns that were created for this original column
                    new_columns = [c for c in df_encoded.columns if c.startswith(f"{col}_")]
                    original_values = df[col].dropna().unique().tolist()
                    
                    # Create mapping for one-hot encoded columns
                    onehot_mapping = {}
                    for i, value in enumerate(original_values):
                        column_name = f"{col}_{value}"
                        if column_name in new_columns:
                            onehot_mapping[str(value)] = column_name
                    
                    categorical_info[col] = {
                        "encoding_method": "onehot",
                        "new_columns": new_columns,
                        "original_values": original_values,
                        "mapping": onehot_mapping,
                        "unique_count": len(original_values)
                    }
        
        return df_encoded, categorical_info
    
    @classmethod
    def _apply_normalization(cls, 
                           df: pd.DataFrame, 
                           method: str,
                           column_config_map: Dict[int, Dict],
                           categorical_info: Dict = None) -> Tuple[pd.DataFrame, Dict]:
        """Apply normalization to specified columns."""
        
        normalization_info = {}
        df_normalized = df.copy()
        
        # Check if any columns have specific normalization settings
        has_column_specific_normalization = False
        if column_config_map:
            for config in column_config_map.values():
                if config:
                    if hasattr(config, 'normalize') and hasattr(config, 'usage'):
                        if config.normalize and config.usage == 'feature':
                            has_column_specific_normalization = True
                            break
                    elif isinstance(config, dict):
                        if config.get('normalize') and config.get('usage') == 'feature':
                            has_column_specific_normalization = True
                            break
        
        # If global method is 'none' and no column-specific normalization, skip
        if method == 'none' and not has_column_specific_normalization:
            return df_normalized, normalization_info
        
        # Identify numeric columns to normalize
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Get list of columns that were label-encoded (should not be normalized)
        label_encoded_columns = []
        if categorical_info:
            for col, info in categorical_info.items():
                if info.get('encoding_method') == 'label':
                    label_encoded_columns.append(col)
        
        # Filter based on column configuration
        columns_to_normalize = []
        for col in numeric_columns:
            # Check if this column should be normalized based on column config
            col_idx = list(df.columns).index(col)
            config = column_config_map.get(col_idx)
            
            # Determine if column should be normalized:
            # 1. If explicit normalize flag is set, use that (respects user's per-column choice)
            # 2. If no explicit config and column is a feature (or no usage specified), normalize by default
            # 3. Skip if column is explicitly marked as 'ignore' or 'label'
            
            # Extract usage and normalize flag from config
            usage = 'feature'  # Default to feature if not specified
            explicit_normalize = None
            
            if config:
                if hasattr(config, 'usage'):
                    usage = config.usage
                elif isinstance(config, dict):
                    usage = config.get('usage', 'feature')
                    
                if hasattr(config, 'normalize'):
                    explicit_normalize = config.normalize
                elif isinstance(config, dict):
                    explicit_normalize = config.get('normalize')
            
            if explicit_normalize is not None:
                # User explicitly set normalization preference for this column
                should_normalize = explicit_normalize and usage == 'feature'
            else:
                # No explicit preference - only normalize if global method is set AND column is a feature
                should_normalize = usage == 'feature' and method != 'none'
            
            # Skip normalization for label-encoded categorical columns
            if should_normalize and col not in label_encoded_columns:
                columns_to_normalize.append(col)
            elif col in label_encoded_columns:
                logger.info(f"Skipping normalization for label-encoded categorical column: {col}")
        
        if not columns_to_normalize:
            logger.info(f"No numeric feature columns found for normalization with method '{method}'")
            return df_normalized, normalization_info
        
        # Always use standard scaler when normalization is requested (ignore method parameter)
        if method in ['standard', 'minmax', 'robust']:
            scaler = StandardScaler()
            df_normalized[columns_to_normalize] = scaler.fit_transform(df[columns_to_normalize])
            
            normalization_info = {
                "method": "standard",
                "original_method_requested": method,
                "columns": columns_to_normalize,
                "means": [float(x) for x in scaler.mean_.tolist()],
                "stds": [float(x) for x in scaler.scale_.tolist()]
            }
        
        else:
            logger.warning(f"Unknown normalization method: {method}. Skipping normalization.")
        
        return df_normalized, normalization_info
    
    @classmethod
    def _finalize_data(cls, df: pd.DataFrame) -> List[List[float]]:
        """Convert processed DataFrame to final numeric format."""
        
        # Ensure all data is numeric
        df_numeric = df.copy()
        
        for col in df_numeric.columns:
            # Convert to numeric, coercing errors to NaN
            df_numeric[col] = pd.to_numeric(df_numeric[col], errors='coerce')
        
        # Check for any remaining non-numeric values
        if df_numeric.isna().any().any():
            problematic_cols = df_numeric.columns[df_numeric.isna().any()].tolist()
            logger.warning(f"Some values could not be converted to numeric in columns: {problematic_cols}. Filling with 0.")
            
            # Show some examples of problematic values
            for col in problematic_cols[:3]:  # Show first 3 problematic columns
                na_indices = df_numeric[col].isna()
                if na_indices.any():
                    original_values = df[col][na_indices].head(3).tolist()
                    logger.warning(f"Column '{col}' - problematic values: {original_values}")
            
            df_numeric = df_numeric.fillna(0)
        
        # Convert to list of lists and ensure no NaN/inf values for JSON serialization
        data_list = df_numeric.values.tolist()
        
        # Replace any remaining NaN or inf values with 0 for JSON compliance
        cleaned_data = []
        for row in data_list:
            cleaned_row = []
            for value in row:
                if pd.isna(value) or np.isinf(value):
                    cleaned_row.append(0.0)
                else:
                    cleaned_row.append(float(value))
            cleaned_data.append(cleaned_row)
        
        return cleaned_data
    
    @classmethod
    def analyze_data_characteristics(cls, data: List[List[Any]], headers: List[str]) -> Dict[str, Any]:
        """Analyze data characteristics to provide processing recommendations."""
        
        df = pd.DataFrame(data, headers)
        
        analysis = {
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "missing_value_count": int(df.isna().sum().sum()),
            "missing_value_percentage": float((df.isna().sum().sum() / (len(df) * len(df.columns))) * 100),
            "column_analysis": []
        }
        
        for col in df.columns:
            series = df[col]
            non_null_series = series.dropna()
            
            col_analysis = {
                "name": str(col),
                "missing_count": int(series.isna().sum()),
                "missing_percentage": float((series.isna().sum() / len(series)) * 100),
                "unique_count": int(len(non_null_series.unique()) if len(non_null_series) > 0 else 0),
                "data_type": str(series.dtype)
            }
            
            # Determine if column is numeric
            if pd.api.types.is_numeric_dtype(series):
                col_analysis["is_numeric"] = True
                mean_val = series.mean()
                std_val = series.std()
                min_val = series.min()
                max_val = series.max()
                
                # Handle NaN values for JSON compliance
                col_analysis["mean"] = float(mean_val) if not pd.isna(mean_val) else 0.0
                col_analysis["std"] = float(std_val) if not pd.isna(std_val) else 0.0
                col_analysis["min"] = float(min_val) if not pd.isna(min_val) else 0.0
                col_analysis["max"] = float(max_val) if not pd.isna(max_val) else 0.0
            else:
                col_analysis["is_numeric"] = False
                # Check if it's categorical
                unique_ratio = len(non_null_series.unique()) / len(non_null_series) if len(non_null_series) > 0 else 0
                col_analysis["is_categorical"] = bool(unique_ratio < 0.5)
                col_analysis["unique_ratio"] = float(unique_ratio)
            
            analysis["column_analysis"].append(col_analysis)
        
        # Provide recommendations
        recommendations = cls._generate_recommendations(analysis)
        analysis["recommendations"] = recommendations
        
        return analysis
    
    @classmethod
    def _generate_recommendations(cls, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate processing recommendations based on data analysis."""
        
        recommendations = {
            "missing_value_strategy": "keep",
            "normalization": "none",
            "categorical_encoding": "label",
            "suggested_feature_columns": [],
            "warnings": []
        }
        
        # Missing value strategy recommendation
        if analysis["missing_value_percentage"] > 50:
            recommendations["missing_value_strategy"] = "fill_mean"
            recommendations["warnings"].append("High percentage of missing values detected")
        elif analysis["missing_value_percentage"] > 10:
            recommendations["missing_value_strategy"] = "fill_median"
        
        # Normalization recommendation
        numeric_columns = [col for col in analysis["column_analysis"] if col.get("is_numeric", False)]
        if len(numeric_columns) > 1:
            # Check if scales are very different
            ranges = []
            for col in numeric_columns:
                if col.get("max") is not None and col.get("min") is not None:
                    ranges.append(col["max"] - col["min"])
            
            if ranges and max(ranges) / min(ranges) > 100:  # Very different scales
                recommendations["normalization"] = "standard"
                recommendations["warnings"].append("Features have very different scales - normalization recommended")
        
        # Feature column recommendations
        for i, col in enumerate(analysis["column_analysis"]):
            if col.get("is_numeric", False) and col["missing_percentage"] < 80:
                recommendations["suggested_feature_columns"].append(i)
        
        return recommendations