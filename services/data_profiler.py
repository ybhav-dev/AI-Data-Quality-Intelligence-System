import pandas as pd
from services.quality_analysis import analyze_quality

def profile_dataset(df: pd.DataFrame, filename: str) -> dict:
    result = analyze_quality(df)
    result["filename"] = filename
    result["columns_preview"] = [str(c) for c in df.columns[:8]]
    return result
