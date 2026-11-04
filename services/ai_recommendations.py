import pandas as pd
import numpy as np

PLACEHOLDERS = {"", "na", "n/a", "null", "none", "nan", "-", "--"}
ID_TOKENS = ("id", "identifier", "index", "code", "zip", "postal", "phone", "account")

def _is_missing(value):
    return pd.isna(value) or str(value).strip().lower() in PLACEHOLDERS

def build_recommendations(df):
    recommendations = []
    for idx, col in enumerate(df.columns):
        series = df[col]
        missing_count = int(series.map(_is_missing).sum())
        if missing_count:
            if pd.api.types.is_numeric_dtype(series):
                fill_value = series.replace([np.inf, -np.inf], np.nan).median()
                strategy = f"Fill {missing_count} missing cells with the column median ({fill_value:g})" if pd.notna(fill_value) else "Review missing numeric values; no safe median is available"
                method = "median"
            else:
                nonmissing = series[~series.map(_is_missing)]
                mode = nonmissing.astype(str).str.strip().mode()
                fill_value = mode.iloc[0] if len(mode) else "Unknown"
                strategy = f"Fill {missing_count} missing cells with the most frequent value ({str(fill_value)[:40]})" if len(mode) else f"Fill {missing_count} missing cells with 'Unknown'"
                method = "mode"
            recommendations.append({
                "id": f"missing_{idx}", "kind": "Missing values", "title": f"Fill missing values in {col}",
                "description": strategy, "impact": f"{missing_count} cells", "priority": "High",
                "column_index": idx, "method": method
            })
        if pd.api.types.is_object_dtype(series.dtype) or pd.api.types.is_string_dtype(series.dtype):
            raw = series.dropna().astype(str)
            trim_count = int((raw != raw.str.strip()).sum())
            if trim_count:
                recommendations.append({
                    "id": f"trim_{idx}", "kind": "Consistency", "title": f"Trim whitespace in {col}",
                    "description": "Remove leading and trailing spaces while preserving the text itself.",
                    "impact": f"{trim_count} values", "priority": "Medium", "column_index": idx, "method": "trim"
                })
            norm = raw.str.strip().str.lower()
            case_count = int((raw.str.strip() != raw.str.strip().str.title()).sum())
            if case_count and (("city" in str(col).lower()) or ("state" in str(col).lower()) or ("category" in str(col).lower())):
                recommendations.append({
                    "id": f"case_{idx}", "kind": "Consistency", "title": f"Standardize capitalization in {col}",
                    "description": "Normalize text to title case for consistent labels.",
                    "impact": f"{case_count} values may change", "priority": "Medium", "column_index": idx, "method": "title"
                })
    duplicate_count = int(df.duplicated().sum())
    if duplicate_count:
        recommendations.append({
            "id": "duplicates_all", "kind": "Duplicates", "title": "Remove exact duplicate rows",
            "description": "Keep the first copy of each identical record and remove repeated copies.",
            "impact": f"{duplicate_count} rows", "priority": "High", "column_index": None, "method": "duplicates"
        })
    # Conservative guidance only: invalid and anomalous values are not changed automatically.
    invalid_examples = []
    anomaly_examples = []
    for col in df.columns:
        name = str(col).lower()
        if "email" in name:
            vals = df[col].dropna().astype(str).str.strip()
            bad = vals[~vals.str.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")]
            if len(bad): invalid_examples.append((str(col), len(bad)))
    if invalid_examples:
        col, count = invalid_examples[0]
        recommendations.append({
            "id": "review_invalid_email", "kind": "Validity", "title": f"Review invalid email values in {col}",
            "description": "These values do not match a basic email pattern. Review or correct them manually; no guessed replacement will be applied.",
            "impact": f"{count} values", "priority": "High", "column_index": None, "method": "manual"
        })
    return recommendations

def apply_recommendations(df, selected_ids, recommendations):
    cleaned = df.copy()
    chosen = {item["id"]: item for item in recommendations if item["id"] in selected_ids}
    for item in chosen.values():
        method = item["method"]
        col_idx = item.get("column_index")
        if method == "duplicates":
            cleaned = cleaned.drop_duplicates(keep="first")
        elif method == "median" and col_idx is not None:
            col = cleaned.columns[col_idx]
            cleaned[col] = cleaned[col].replace(list(PLACEHOLDERS), np.nan)
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
            median = cleaned[col].median()
            if pd.notna(median): cleaned[col] = cleaned[col].fillna(median)
        elif method == "mode" and col_idx is not None:
            col = cleaned.columns[col_idx]
            cleaned[col] = cleaned[col].replace(list(PLACEHOLDERS), np.nan)
            mode = cleaned[col].dropna().astype(str).str.strip().mode()
            fill = mode.iloc[0] if len(mode) else "Unknown"
            cleaned[col] = cleaned[col].fillna(fill)
        elif method == "trim" and col_idx is not None:
            col = cleaned.columns[col_idx]
            cleaned[col] = cleaned[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        elif method == "title" and col_idx is not None:
            col = cleaned.columns[col_idx]
            cleaned[col] = cleaned[col].map(lambda x: x.strip().title() if isinstance(x, str) else x)
    return cleaned
