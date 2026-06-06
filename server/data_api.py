from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import io
from pydantic import BaseModel
from sklearn.preprocessing import StandardScaler, MinMaxScaler


from server.ship_cache_service import ShipCacheService

router = APIRouter()
# Use a single cache instance for the module
cache = ShipCacheService()

# --- Pydantic Models for Requests ---
class ColumnActionRequest(BaseModel):
    action: str # 'ignore' or 'include'
    column_index: int

class NormalizationRequest(BaseModel):
    method: str # 'standard', 'minmax', 'none'

class HeaderRowRequest(BaseModel):
    row_index: int

# --- Helper Functions ---
def get_cache_key(filename: str, suffix: str = "original"):
    # Simple session management for now
    user_session_id = "user_session_1" 
    return f"{user_session_id}_{filename}_{suffix}"

def detect_column_types(df: pd.DataFrame):
    types = []
    for col in df.columns:
        # Attempt to convert to numeric, ignoring errors
        numeric_col = pd.to_numeric(df[col], errors='coerce')
        if numeric_col.isna().all():
             types.append('categorical')
             continue
        
        # Check if all non-NaN values are integers
        if (numeric_col.dropna() % 1 == 0).all():
            types.append('integer')
        else:
            types.append('numeric')
    return types


# --- API Endpoints ---
@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Handles CSV file uploads, parses them, and stores them in the cache.
    Returns initial data preview and metadata.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")

    try:
        contents = await file.read()
        # Store original raw content
        raw_key = get_cache_key(file.filename, "raw")
        cache.set(raw_key, contents)

        # Attempt to parse with headers, then without
        try:
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
            has_headers = True
        except Exception:
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')), header=None)
            has_headers = False
        
        # Store the processed dataframe
        df_key = get_cache_key(file.filename, "processed")
        cache.set(df_key, df)

        column_types = detect_column_types(df)

        return JSONResponse(status_code=200, content={
            "message": "File uploaded successfully",
            "filename": file.filename,
            "data": df.to_json(orient='split'),
            "metadata": {
                "rowCount": len(df),
                "columnCount": len(df.columns),
                "hasHeaders": has_headers,
                "columnTypes": column_types,
                "preview": df.head().to_json(orient='split')
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {e}")


@router.post("/api/data/{filename}/set_header")
async def set_header(filename: str, request: HeaderRowRequest):
    """
    Sets a specific row as the header for the dataset.
    """
    raw_key = get_cache_key(filename, "raw")
    contents = cache.get(raw_key)
    if contents is None:
        raise HTTPException(status_code=404, detail="Original file data not found. Please upload again.")

    try:
        # Re-parse from original content with the specified header row
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')), header=request.row_index)
        
        df_key = get_cache_key(filename, "processed")
        cache.set(df_key, df) # Overwrite the processed dataframe

        column_types = detect_column_types(df)

        return JSONResponse(status_code=200, content={
            "message": f"Row {request.row_index} set as header.",
            "data": df.to_json(orient='split'),
            "metadata": {
                "rowCount": len(df),
                "columnCount": len(df.columns),
                "hasHeaders": True,
                "columnTypes": column_types,
                "preview": df.head().to_json(orient='split')
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set header: {e}")


@router.post("/api/data/{filename}/normalize")
async def normalize_data(filename: str, request: NormalizationRequest):
    """
    Applies normalization to the dataset.
    """
    df_key = get_cache_key(filename, "processed")
    df = cache.get(df_key)

    if df is None:
        raise HTTPException(status_code=404, detail="Processed data not found.")

    # Select only numeric columns for normalization
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) == 0:
        raise HTTPException(status_code=400, detail="No numeric columns to normalize.")

    if request.method == 'none':
        # This would require fetching the original df again if we want to revert
        # For now, we just return the current state
        normalized_df = df
    elif request.method == 'standard':
        scaler = StandardScaler()
        df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    elif request.method == 'minmax':
        scaler = MinMaxScaler()
        df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    else:
        raise HTTPException(status_code=400, detail="Invalid normalization method.")

    cache.set(df_key, df) # Update the cached dataframe

    return JSONResponse(status_code=200, content={
        "message": f"Normalization '{request.method}' applied.",
        "data": df.to_json(orient='split'),
    })