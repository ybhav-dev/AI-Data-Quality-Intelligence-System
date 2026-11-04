import os
import re
import pandas as pd
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from services.quality_analysis import analyze_quality

analysis_bp = Blueprint("analysis", __name__)

def _build_insights(df):
    """Generate quality findings plus domain-aware business insights using transparent heuristics."""
    quality, quality_recs, business, business_recs = [], [], [], []
    nrows, ncols = df.shape
    if nrows and ncols:
        quality.append({"title":"Dataset size", "text":f"The dataset contains {nrows:,} records across {ncols} columns."})
    missing = df.isna().sum()
    for name, pct in (missing / max(nrows, 1) * 100).sort_values(ascending=False).head(5).items():
        if pct > 0:
            quality.append({"title":"Missing data", "text":f"'{name}' has {int(missing[name]):,} missing values ({pct:.1f}% of rows)."})
            quality_recs.append({"title":f"Address blanks in '{name}'", "text":"Validate the source or use a documented fill strategy before relying on this field."})
    numeric = df.select_dtypes(include="number")
    for col in numeric.columns:
        vals=df[col].dropna()
        if len(vals)>=4:
            q1,q3=vals.quantile([.25,.75]); iqr=q3-q1
            count=int(((vals<q1-1.5*iqr)|(vals>q3+1.5*iqr)).sum()) if iqr else 0
            if count:
                quality.append({"title":"Potential outliers","text":f"'{col}' has {count:,} potential outlier(s) using the 1.5×IQR rule."})
                quality_recs.append({"title":f"Inspect outliers in '{col}'","text":"Check whether extreme values are valid business cases or data-entry errors; avoid removing them automatically."})

    # Infer likely business fields from column names; only report metrics when a suitable field exists.
    def find_col(tokens, numeric_only=False, exclude=()):
        candidates=[]
        for c in df.columns:
            name=str(c).lower().replace(" ","_")
            if any(t in name for t in tokens) and not any(t in name for t in exclude):
                if not numeric_only or pd.api.types.is_numeric_dtype(df[c]): candidates.append(c)
        return candidates[0] if candidates else None
    amount=find_col(["revenue","sales","order_amount","amount","total","price"],True,exclude=("unit_price","price_per"))
    qty=find_col(["quantity","qty","units"],True)
    price=find_col(["unit_price","price_per","price"],True)
    category=find_col(["category","product","item","segment","department","type"])
    location=find_col(["city","state","region","country","location"])
    customer=find_col(["customer_id","customer","client","user_id"])
    rating=find_col(["rating","review_score","satisfaction"],True)
    date_col=None
    for c in df.columns:
        if any(t in str(c).lower() for t in ["date","time","created_at","order_day"]):
            parsed=pd.to_datetime(df[c],errors="coerce")
            if parsed.notna().sum()>=3: date_col=c; break

    def top_group(col, metric=None, agg="sum"):
        if not col: return None
        temp=df.copy()
        temp[col]=temp[col].astype("string")
        if metric:
            temp[metric]=pd.to_numeric(temp[metric],errors="coerce")
            grouped=temp.dropna(subset=[col,metric]).groupby(col)[metric]
            result=grouped.sum() if agg=="sum" else grouped.mean()
        else:
            result=temp[col].dropna().value_counts()
        return result.sort_values(ascending=False) if len(result) else None

    if amount:
        vals=pd.to_numeric(df[amount],errors="coerce").dropna()
        if len(vals):
            business.append({"title":"Revenue / amount overview","text":f"'{amount}' totals {vals.sum():,.2f} across {len(vals):,} usable records; average value is {vals.mean():,.2f}."})
            business_recs.append({"title":"Review high-value transactions","text":"Compare unusually large transactions with order details and business rules before treating them as errors."})
    if qty and amount:
        q=pd.to_numeric(df[qty],errors="coerce"); a=pd.to_numeric(df[amount],errors="coerce")
        valid=q.notna() & a.notna()
        if valid.sum()>=3:
            corr=q[valid].corr(a[valid])
            if pd.notna(corr): business.append({"title":"Quantity and value relationship","text":f"'{qty}' and '{amount}' have a {('positive' if corr>=0 else 'negative')} association (r = {corr:.2f}) across {int(valid.sum()):,} records."})
    for group_col,label in [(category,"category/product"),(location,"location")]:
        if group_col:
            grouped=top_group(group_col,amount,"sum") if amount else top_group(group_col)
            if grouped is not None and len(grouped):
                top_name,top_val=grouped.index[0],grouped.iloc[0]
                if amount:
                    business.append({"title":f"Top {label} by value","text":f"'{top_name}' leads in '{group_col}' with {top_val:,.2f} in '{amount}'."})
                    if len(grouped)>1:
                        low_name,low_val=grouped.index[-1],grouped.iloc[-1]
                        business.append({"title":f"Lowest {label} by value","text":f"'{low_name}' has the lowest total '{amount}' ({low_val:,.2f}) among groups with usable values."})
                    business_recs.append({"title":f"Compare performance across {group_col}","text":f"Compare volume, average transaction value, and product mix for the leading and lower-performing groups before deciding where to invest."})
                else:
                    business.append({"title":f"Most frequent {label}","text":f"'{top_name}' appears most often in '{group_col}' ({int(top_val):,} records)."})
    if customer:
        counts=df[customer].dropna().astype(str).value_counts()
        if len(counts):
            repeats=int((counts>1).sum())
            business.append({"title":"Customer activity","text":f"{repeats:,} distinct values in '{customer}' appear more than once, indicating repeat records or activity (confirm the field represents customer identity)."})
            if amount:
                tmp=df.assign(_cust=df[customer].astype(str),_amt=pd.to_numeric(df[amount],errors="coerce"))
                spend=tmp.dropna(subset=["_amt"]).groupby("_cust")["_amt"].sum().sort_values(ascending=False)
                if len(spend): business.append({"title":"Highest-spend customer","text":f"'{spend.index[0]}' has the highest summed '{amount}' ({spend.iloc[0]:,.2f})."})
    if rating:
        vals=pd.to_numeric(df[rating],errors="coerce").dropna()
        if len(vals):
            business.append({"title":"Rating overview","text":f"Average '{rating}' is {vals.mean():.2f} across {len(vals):,} numeric ratings (range {vals.min():g}–{vals.max():g})."})
            business_recs.append({"title":"Investigate low ratings","text":"Review low-rated records alongside product, location, and order details to identify recurring service or product issues."})
    if date_col and amount:
        tmp=df.copy(); tmp["_date"]=pd.to_datetime(tmp[date_col],errors="coerce"); tmp["_amount"]=pd.to_numeric(tmp[amount],errors="coerce")
        monthly=tmp.dropna(subset=["_date","_amount"]).groupby(tmp["_date"].dt.to_period("M"))["_amount"].sum().sort_index()
        if len(monthly)>=2:
            first,last=monthly.iloc[0],monthly.iloc[-1]
            change=((last-first)/abs(first)*100) if first else None
            if change is not None:
                business.append({"title":"Period trend","text":f"Summed '{amount}' changed {change:+.1f}% from {monthly.index[0]} ({first:,.2f}) to {monthly.index[-1]} ({last:,.2f})."})
                business_recs.append({"title":"Review period-over-period changes","text":"Check seasonality, promotions, and data completeness before attributing the change to business performance."})
    if numeric.shape[1]>=2:
        corr=numeric.corr(); cols=list(corr.columns); pairs=[]
        for i in range(len(cols)):
            for j in range(i+1,len(cols)):
                v=corr.iloc[i,j]
                if pd.notna(v) and abs(v)>=.7: pairs.append((abs(v),v,cols[i],cols[j]))
        for _,v,a,b in sorted(pairs,reverse=True)[:3]:
            business.append({"title":"Strong numeric relationship","text":f"'{a}' and '{b}' show a {'positive' if v>0 else 'negative'} association (r = {v:.2f}); this does not establish causation."})
            business_recs.append({"title":f"Explore '{a}' vs '{b}'","text":"Investigate the relationship with domain context and check for confounding factors."})
    if not business:
        business.append({"title":"Business analysis not inferred","text":"No clear revenue, category, customer, rating, or date fields were detected. Rename columns descriptively or use the chart tools for manual exploration."})
    if not quality: quality=[{"title":"Quality overview","text":"No major missing-value or outlier findings were detected by these checks."}]
    if not quality_recs: quality_recs=[{"title":"Maintain data quality","text":"Continue validating key fields against documented business rules."}]
    if not business_recs: business_recs=[{"title":"Explore group differences","text":"Compare relevant categories and metrics, and validate findings with business context."}]
    return quality[:12], quality_recs[:10], business[:12], business_recs[:10]

def _read_dataset(path):
    ext = os.path.splitext(path.lower())[1]
    return pd.read_csv(path) if ext == ".csv" else pd.read_excel(path)


@analysis_bp.post("/analysis/validate-rules")
def validate_custom_rules():
    path=session.get("latest_dataset_path")
    if not path or not os.path.exists(path):
        return jsonify({"error":"Upload a dataset first."}),400
    try:
        df=_read_dataset(path)
        payload=request.get_json(silent=True) or {}
        rules=payload.get("rules",[])
        if not isinstance(rules,list) or len(rules)>30:
            return jsonify({"error":"Provide up to 30 validation rules."}),400
        results=[]
        for idx,rule in enumerate(rules,1):
            col=rule.get("column")
            kind=rule.get("type")
            if col not in df.columns:
                results.append({"rule":idx,"column":str(col),"type":kind,"failed":0,"examples":[],"error":"Column not found"})
                continue
            series=df[col]
            failed_mask=pd.Series(False,index=df.index)
            detail=""
            if kind=="not_null":
                failed_mask=series.isna() | series.astype(str).str.strip().str.lower().isin(["","na","n/a","null","none","nan"])
                detail="Value must not be empty"
            elif kind=="unique":
                failed_mask=series.notna() & series.duplicated(keep=False)
                detail="Value must be unique"
            elif kind=="email":
                values=series.astype(str).str.strip()
                failed_mask=series.notna() & ~values.str.match(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$",na=False)
                detail="Value must be a valid email address"
            elif kind in {"min","max","between"}:
                numeric=pd.to_numeric(series,errors="coerce")
                try:
                    low=float(rule.get("min")) if kind in {"min","between"} else None
                    high=float(rule.get("max")) if kind in {"max","between"} else float(rule.get("value"))
                except (TypeError,ValueError):
                    results.append({"rule":idx,"column":str(col),"type":kind,"failed":0,"examples":[],"error":"Enter valid numeric bounds"})
                    continue
                failed_mask=series.notna() & numeric.isna()
                if low is not None: failed_mask |= numeric.notna() & (numeric<low)
                if high is not None: failed_mask |= numeric.notna() & (numeric>high)
                detail=f"Value must be numeric"+(f" and ≥ {low:g}" if low is not None else "")+(f" and ≤ {high:g}" if high is not None else "")
            elif kind=="regex":
                pattern=str(rule.get("value",""))
                if not pattern or len(pattern)>200:
                    results.append({"rule":idx,"column":str(col),"type":kind,"failed":0,"examples":[],"error":"Provide a pattern (max 200 characters)"})
                    continue
                try: failed_mask=series.notna() & ~series.astype(str).str.match(pattern,na=False)
                except re.error:
                    results.append({"rule":idx,"column":str(col),"type":kind,"failed":0,"examples":[],"error":"Invalid regular expression"})
                    continue
                detail="Value must match the pattern"
            else:
                results.append({"rule":idx,"column":str(col),"type":str(kind),"failed":0,"examples":[],"error":"Unsupported rule"})
                continue
            bad=df.loc[failed_mask]
            examples=[{"row":int(i)+1,"value":str(df.at[i,col])[:120]} for i in bad.index[:5]]
            results.append({"rule":idx,"column":str(col),"type":kind,"failed":int(failed_mask.sum()),"examples":examples,"description":detail})
        return jsonify({"results":results,"total_rules":len(results),"failed_records":sum(x.get("failed",0) for x in results)})
    except Exception as exc:
        return jsonify({"error":f"Could not validate rules: {exc}"}),400

@analysis_bp.get("/business-insights")
def business_insights_page():
    path = session.get("latest_dataset_path")
    filename = session.get("latest_dataset_name", "Dataset")
    if not path or not os.path.exists(path):
        return render_template("business_insights.html", has_dataset=False, filename=None,
            business_insights=[], business_recommendations=[])
    try:
        df = _read_dataset(path)
        _, _, business_insights, business_recommendations = _build_insights(df)
        return render_template("business_insights.html", has_dataset=True, filename=filename,
            rows=len(df), columns=len(df.columns), business_insights=business_insights,
            business_recommendations=business_recommendations)
    except Exception as exc:
        return render_template("business_insights.html", has_dataset=False, filename=filename,
            business_insights=[], business_recommendations=[], error=str(exc))

@analysis_bp.get("/analysis")
def analysis_page():
    path = session.get("latest_dataset_path")
    filename = session.get("latest_dataset_name", "Dataset")
    if not path or not os.path.exists(path):
        return render_template("analysis.html", has_dataset=False, filename=None,
                               issues=[], counts={}, dimensions={}, chart_profiles=[], correlation_data={})

    try:
        df = _read_dataset(path)
        summary = analyze_quality(df)
        insights, recommendations, _, _ = _build_insights(df)
        issues = []
        placeholders = {"", "na", "n/a", "null", "none", "nan", "-", "--"}

        # Missing and placeholder values: include each affected cell.
        for row_idx, row in df.iterrows():
            for col in df.columns:
                value = row[col]
                missing = pd.isna(value) or str(value).strip().lower() in placeholders
                if missing:
                    issues.append({"type":"Missing value","row":int(row_idx)+1,
                        "column":str(col),"value":"(blank)","reason":"Field is empty or contains a missing-value placeholder"})

        # Duplicate records: list every row that repeats an earlier row.
        duplicate_mask = df.duplicated(keep="first")
        for row_idx in df.index[duplicate_mask]:
            issues.append({"type":"Duplicate row","row":int(row_idx)+1,
                "column":"—","value":"—","reason":"Entire record duplicates an earlier row"})

        # Use the analyzer's detailed validation and consistency findings.
        for item in summary.get("examples", []):
            issue = item.get("issue","")
            if "anomaly" in issue.lower() or "outlier" in issue.lower():
                kind = "Anomaly"
            elif any(word in issue.lower() for word in ["mismatch","inconsistent","whitespace","capitalization","spelling"]):
                kind = "Consistency"
            else:
                kind = "Invalid data"
            issues.append({"type":kind,"row":item.get("row","—"),
                "column":item.get("column","—"),"value":item.get("value","—"),
                "reason":issue})

        # De-duplicate repeated reports for the same issue/type/record/column.
        deduped = []
        seen = set()
        for issue_item in issues:
            key = (issue_item["type"], issue_item["row"], issue_item["column"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(issue_item)
        issues = deduped

        # Keep category cards and the findings table numerically consistent.
        counts = {label: sum(1 for item in issues if item["type"] == label)
                  for label in ["Missing value", "Duplicate row", "Invalid data", "Consistency", "Anomaly"]}

        # Lightweight column profiles for interactive charts.
        chart_profiles = []
        # Correlation matrix for numeric columns (bounded to keep the page responsive).
        numeric_frame = df.select_dtypes(include="number")
        if numeric_frame.shape[1] < 2:
            converted = {}
            for col in df.columns:
                candidate = pd.to_numeric(df[col], errors="coerce")
                if candidate.notna().mean() >= 0.85 and candidate.nunique(dropna=True) > 1:
                    converted[str(col)] = candidate
            numeric_frame = pd.DataFrame(converted, index=df.index)
        numeric_frame = numeric_frame.loc[:, numeric_frame.nunique(dropna=True) > 1].iloc[:, :12]
        correlation_data = {}
        if numeric_frame.shape[1] >= 2:
            corr = numeric_frame.corr().fillna(0).round(3)
            correlation_data = {
                "columns": [str(c) for c in corr.columns],
                "values": [[float(v) for v in row] for row in corr.values]
            }
        for col in df.columns:
            series = df[col].dropna()
            if series.empty:
                continue
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().mean() >= 0.85 and numeric.nunique() > 1:
                vals = numeric.dropna()
                chart_profiles.append({
                    "column": str(col), "kind": "numeric",
                    "values": [float(v) for v in vals.iloc[:1500]],
                    "count": int(vals.size),
                    "mean": round(float(vals.mean()), 3),
                    "median": round(float(vals.median()), 3),
                    "min": round(float(vals.min()), 3),
                    "max": round(float(vals.max()), 3)
                })
            else:
                vc = series.astype(str).value_counts().head(12)
                chart_profiles.append({
                    "column": str(col), "kind": "categorical",
                    "labels": [str(v) for v in vc.index],
                    "values": [int(v) for v in vc.values],
                    "count": int(series.size),
                    "unique": int(series.nunique())
                })

        return render_template("analysis.html", has_dataset=True, filename=filename,
            chart_profiles=chart_profiles, correlation_data=correlation_data,
            issues=issues, counts=counts, dimensions=summary.get("dimensions",{}),
            rows=summary.get("rows",0), columns=summary.get("columns",0), column_names=[str(c) for c in df.columns],
            quality_score=summary.get("quality_score",0), insights=insights, recommendations=recommendations)
    except Exception as exc:
        return render_template("analysis.html", has_dataset=False, filename=filename,
            issues=[], counts={}, dimensions={}, chart_profiles=[], correlation_data={}, insights=[], recommendations=[], error=str(exc))
