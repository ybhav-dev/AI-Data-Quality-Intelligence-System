import re
import pandas as pd
import numpy as np

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
CITY_STATE = {
    "delhi": "delhi", "mumbai": "maharashtra", "bengaluru": "karnataka",
    "hyderabad": "telangana", "pune": "maharashtra", "jaipur": "rajasthan",
    "chennai": "tamil nadu", "kolkata": "west bengal",
    "gurugram": "haryana", "noida": "uttar pradesh"
}

def _norm(value):
    if pd.isna(value):
        return ""
    return str(value).strip().lower()

def analyze_quality(df: pd.DataFrame) -> dict:
    rows, cols = df.shape
    total_cells = max(rows * cols, 1)
    missing_mask = df.isna()
    # Treat common placeholder strings as missing too.
    placeholders = {"", "na", "n/a", "null", "none", "nan", "-", "--"}
    placeholder_mask = df.map(lambda x: _norm(x) in placeholders)
    missing_mask = missing_mask | placeholder_mask
    missing_count = int(missing_mask.sum().sum())
    duplicate_count = int(df.duplicated().sum())

    invalid_cells = set()
    consistency_cells = set()
    anomaly_cells = set()
    examples = []

    lower_to_col = {str(c).strip().lower(): c for c in df.columns}
    def col_like(*tokens):
        for c in df.columns:
            cl = str(c).strip().lower()
            if any(t in cl for t in tokens):
                return c
        return None

    email_col = col_like("email", "e-mail")
    age_col = col_like("age")
    rating_col = col_like("rating", "stars")
    qty_col = col_like("quantity", "qty")
    price_col = col_like("price", "amount", "revenue", "total", "cost")
    date_col = col_like("date")
    city_col = col_like("city")
    state_col = col_like("state", "province")
    category_col = col_like("category", "type")

    def add_issue(bucket, row_idx, col, value, reason):
        bucket.add((int(row_idx), str(col)))
        if len(examples) < 5000:
            examples.append({"row": int(row_idx)+1, "column": str(col),
                             "value": str(value)[:80], "issue": reason})

    if email_col is not None:
        for idx, value in df[email_col].items():
            val = _norm(value)
            if val and val not in placeholders and not EMAIL_RE.match(val):
                add_issue(invalid_cells, idx, email_col, value, "Invalid email format")

    for col, lo, hi, reason in [
        (age_col, 0, 120, "Age outside expected range (0–120)"),
        (rating_col, 1, 5, "Rating outside expected range (1–5)"),
        (qty_col, 1, None, "Quantity must be positive"),
        (price_col, 0, None, "Price/amount cannot be negative")
    ]:
        if col is None: continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        for idx, value in numeric.items():
            if pd.isna(value): continue
            if (lo is not None and value < lo) or (hi is not None and value > hi):
                add_issue(invalid_cells, idx, col, value, reason)

    if date_col is not None:
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        for idx, value in df[date_col].items():
            if _norm(value) and pd.isna(parsed.loc[idx]):
                add_issue(invalid_cells, idx, date_col, value, "Invalid date")

    if city_col is not None:
        # Flag casing/whitespace variants and known city spelling variants.
        for idx, value in df[city_col].items():
            raw = str(value) if not pd.isna(value) else ""
            norm = _norm(value)
            if norm and raw != raw.strip():
                add_issue(consistency_cells, idx, city_col, value, "Leading/trailing whitespace")
            if norm and norm in CITY_STATE and raw.strip() != raw.strip().title():
                add_issue(consistency_cells, idx, city_col, value, "Inconsistent capitalization")

    if category_col is not None:
        known = set(_norm(x) for x in df[category_col].dropna().unique())
        canonical = {"electronic": "electronics", "electonics": "electronics"}
        for idx, value in df[category_col].items():
            norm = _norm(value)
            if norm in canonical:
                add_issue(consistency_cells, idx, category_col, value, "Possible category spelling inconsistency")

    if city_col is not None and state_col is not None:
        for idx, row in df[[city_col, state_col]].iterrows():
            city, state = _norm(row[city_col]), _norm(row[state_col])
            expected = CITY_STATE.get(city)
            if expected and state and state != expected:
                add_issue(consistency_cells, idx, state_col, row[state_col], "City/state mismatch")

    # Robust univariate anomaly detection using IQR.
    # Exclude identifier-like columns and avoid flagging small samples.
    anomaly_row_columns = {}
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    id_tokens = ("id", "identifier", "index", "code", "zip", "postal", "phone", "account")
    for col in numeric_cols:
        col_name = str(col).strip().lower()
        if any(token in col_name for token in id_tokens):
            continue
        series = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(series) < 8 or series.nunique() < 8:
            continue
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        if not np.isfinite(iqr) or iqr <= 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        for idx, value in pd.to_numeric(df[col], errors="coerce").items():
            if pd.notna(value) and (value < lower or value > upper):
                anomaly_cells.add((int(idx), str(col)))
                anomaly_row_columns.setdefault(int(idx), []).append(str(col))
                if len(examples) < 5000:
                    examples.append({
                        "row": int(idx) + 1,
                        "column": str(col),
                        "value": str(value)[:80],
                        "issue": f"Potential numeric outlier (IQR bounds: {lower:.2f} to {upper:.2f})"
                    })

    # Dimension scores are based on the appropriate denominator and retain
    # precision until display. Row-based dimensions are more sensitive than
    # dividing every issue by all cells in a wide dataset.
    row_denominator = max(rows, 1)
    completeness = max(0.0, 100 * (1 - missing_count / total_cells))
    uniqueness = max(0.0, 100 * (1 - duplicate_count / row_denominator))
    validity = max(0.0, 100 * (1 - len({r for r, _ in invalid_cells}) / row_denominator))
    consistency = max(0.0, 100 * (1 - len({r for r, _ in consistency_cells}) / row_denominator))
    reliability = max(0.0, 100 * (1 - len({r for r, _ in invalid_cells} | {r for r, _ in anomaly_cells}) / row_denominator))
    dimensions = {
        "completeness": round(completeness, 1),
        "validity": round(validity, 1),
        "uniqueness": round(uniqueness, 1),
        "consistency": round(consistency, 1),
        "reliability": round(reliability, 1)
    }
    # Overall score combines dimension quality with a direct issue-rate penalty,
    # so a small number of problems does not disappear when rounded.
    issue_rows = (
        len({r for r, _ in invalid_cells}) +
        len({r for r, _ in consistency_cells}) +
        duplicate_count +
        len({r for r, _ in anomaly_cells})
    )
    issue_rate_penalty = min(35.0, 35.0 * issue_rows / row_denominator)
    score = max(0, min(100, round(sum(dimensions.values()) / len(dimensions) - issue_rate_penalty)))
    issues = {
        "missing_values": missing_count,
        "duplicates": duplicate_count,
        "invalid_data": len(invalid_cells),
        "anomalies": len(anomaly_cells),
        "consistency_issues": len(consistency_cells)
    }
    return {
        "rows": rows, "columns": cols, "quality_score": score,
        "missing_values": missing_count, "duplicate_rows": duplicate_count,
        "anomalies": len(anomaly_cells), "invalid_values": len(invalid_cells),
        "consistency_issues": len(consistency_cells),
        "dimensions": dimensions, "issue_distribution": issues,
        "examples": examples
    }
