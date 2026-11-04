import os, uuid, shutil
import pandas as pd
import numpy as np
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, send_file, flash

cleaning_bp = Blueprint("cleaning", __name__)

def _read_current():
    path = session.get("latest_dataset_path")
    if not path or not os.path.exists(path): return None, None
    ext = os.path.splitext(path.lower())[1]
    df = pd.read_csv(path) if ext == ".csv" else pd.read_excel(path)
    # Drop accidental index artifacts only when the header is blank/index-like
    # and the values are either empty or a simple sequential row index.
    for col in list(df.columns):
        name = str(col).strip().lower()
        if name.startswith("unnamed:") or name in {"nan", "none", "", "index"}:
            vals = df[col]
            numeric = pd.to_numeric(vals, errors="coerce")
            expected0 = pd.Series(range(len(df)), index=df.index)
            expected1 = pd.Series(range(1, len(df)+1), index=df.index)
            is_sequence = numeric.notna().all() and (
                numeric.reset_index(drop=True).equals(expected0.reset_index(drop=True)) or
                numeric.reset_index(drop=True).equals(expected1.reset_index(drop=True))
            )
            if vals.isna().all() or is_sequence:
                df = df.drop(columns=[col])
    # Avoid duplicate/blank headers causing ambiguous table/profile behavior.
    cleaned_names=[]
    seen={}
    for i, col in enumerate(df.columns):
        label=str(col).strip()
        if not label or label.lower() in {"nan", "none"}:
            label=f"Column {i+1}"
        count=seen.get(label,0)
        seen[label]=count+1
        cleaned_names.append(label if count==0 else f"{label}_{count+1}")
    df.columns=cleaned_names
    return df, session.get("latest_dataset_name", "Dataset")

def _read_working():
    path = session.get("cleaning_working_path")
    if path and os.path.exists(path):
        df = pd.read_csv(path)
        # Defensive cleanup for working copies created by earlier versions.
        drop=[]
        for col in df.columns:
            name=str(col).strip().lower()
            if name.startswith("unnamed:") or name in {"nan", "none", "", "index"}:
                vals=pd.to_numeric(df[col],errors="coerce")
                seq0=pd.Series(range(len(df)))
                seq1=pd.Series(range(1,len(df)+1))
                if df[col].isna().all() or (vals.notna().all() and (vals.reset_index(drop=True).equals(seq0) or vals.reset_index(drop=True).equals(seq1))):
                    drop.append(col)
        if drop: df=df.drop(columns=drop)
        return df
    df, _ = _read_current()
    return df

def _ensure_working():
    path = session.get("cleaning_working_path")
    if path and os.path.exists(path):
        return path
    df, _ = _read_current()
    if df is None:
        return None
    out_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)),"outputs")
    os.makedirs(out_dir,exist_ok=True)
    path=os.path.join(out_dir,f"working_{uuid.uuid4().hex}.csv")
    df.to_csv(path,index=False)
    session["cleaning_working_path"]=path
    session["cleaning_undo_path"]=None
    return path

def _clean(df, operations):
    out = df.copy()
    if "trim" in operations:
        for col in out.select_dtypes(include=["object", "string"]).columns:
            out[col] = out[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    if "standardize_case" in operations:
        for col in out.select_dtypes(include=["object", "string"]).columns:
            name = str(col).lower()
            if any(token in name for token in ["email", "url", "website", "phone", "id", "code"]):
                continue
            out[col] = out[col].map(lambda x: x.strip().title() if isinstance(x, str) else x)
    if "fill_missing" in operations:
        placeholders = ["", "na", "n/a", "null", "none", "nan", "-", "--"]
        for col in out.columns:
            s = out[col].replace(placeholders, np.nan)
            if pd.api.types.is_numeric_dtype(s):
                fill = pd.to_numeric(s, errors="coerce").median()
                if pd.notna(fill): out[col] = s.fillna(fill)
            else:
                mode = s.dropna().astype(str).str.strip().mode()
                out[col] = s.fillna(mode.iloc[0] if len(mode) else "Unknown")
    if "drop_missing_rows" in operations:
        placeholders = ["", "na", "n/a", "null", "none", "nan", "-", "--"]
        out = out.replace(placeholders, np.nan).dropna()
    if "drop_duplicates" in operations:
        out = out.drop_duplicates(keep="first")
    return out

def _operations():
    return request.form.getlist("operations")

@cleaning_bp.get("/cleaning")
def cleaning_page():
    df, filename = _read_current()
    if df is None:
        return render_template("cleaning.html", has_dataset=False, filename=None, preview=[], columns=[], rows=0, missing=0, duplicates=0)
    preview = df.head(10).where(pd.notna(df.head(10)), "").to_dict(orient="records")
    return render_template("cleaning.html", has_dataset=True, filename=filename,
        rows=len(df), columns=list(map(str,df.columns)), preview=preview,
        missing=int(df.isna().sum().sum()), duplicates=int(df.duplicated().sum()),
        column_count=len(df.columns))

@cleaning_bp.post("/cleaning/preview")
def cleaning_preview():
    df = _read_working()
    if df is None: return jsonify({"error":"Upload a dataset first."}),400
    operations = _operations()
    cleaned = _clean(df, operations)
    return jsonify({
        "rows_before":len(df),"rows_after":len(cleaned),
        "missing_before":int(df.isna().sum().sum()),"missing_after":int(cleaned.isna().sum().sum()),
        "duplicates_before":int(df.duplicated().sum()),"duplicates_after":int(cleaned.duplicated().sum()),
        "columns":list(map(str,cleaned.columns)),
        "preview":cleaned.head(10).where(pd.notna(cleaned.head(10)),"").to_dict(orient="records"),
        "selected":operations
    })

@cleaning_bp.get("/cleaning/table")
def cleaning_table():
    df = _read_working()
    if df is None: return jsonify({"error":"Upload a dataset first."}),400
    query=request.args.get("q","").strip().lower()
    sort_col=request.args.get("sort","")
    direction=request.args.get("direction","asc")
    page=max(1,int(request.args.get("page",1)))
    page_size=min(100,max(10,int(request.args.get("page_size",25))))
    view=df.copy()
    if query:
        mask=view.astype(str).apply(lambda col: col.str.lower().str.contains(query,regex=False,na=False)).any(axis=1)
        view=view[mask]
    if sort_col in view.columns:
        try: view=view.sort_values(sort_col,ascending=(direction!="desc"),kind="stable",na_position="last")
        except Exception: pass
    total=len(view)
    start=(page-1)*page_size
    page_view=view.iloc[start:start+page_size].copy()
    page_view["_row_index"] = page_view.index
    rows=page_view.where(pd.notna(page_view),"").to_dict(orient="records")
    return jsonify({"columns":list(map(str,df.columns)),"rows":rows,"page":page,"page_size":page_size,"total":total,"pages":max(1,(total+page_size-1)//page_size),"working":bool(session.get("cleaning_working_path"))})

@cleaning_bp.get("/cleaning/profile/<path:column>")
def cleaning_profile(column):
    df=_read_working()
    if df is None or column not in df.columns: return jsonify({"error":"Column not found."}),404
    col=df[column]
    blank_mask=col.astype(str).str.strip().isin(["", "na", "n/a", "null", "none", "nan", "-"])
    missing=int(col.isna().sum()+((~col.isna()) & blank_mask).sum())
    vals=col[~col.isna() & ~blank_mask]
    profile={"column":str(column),"dtype":str(col.dtype),"total":len(col),"missing":missing,
             "unique":int(vals.nunique(dropna=True)),"top_values":vals.astype(str).value_counts().head(8).to_dict()}
    numeric=pd.to_numeric(col,errors="coerce")
    numeric_values=numeric.dropna()
    if pd.api.types.is_numeric_dtype(col):
        profile["stats"]={"min":None if numeric_values.empty else float(numeric_values.min()),
          "median":None if numeric_values.empty else float(numeric_values.median()),
          "mean":None if numeric_values.empty else float(numeric_values.mean()),
          "max":None if numeric_values.empty else float(numeric_values.max())}
        if not numeric_values.empty:
            counts, edges=np.histogram(numeric_values, bins=min(8, max(3, int(np.sqrt(len(numeric_values))))))
            profile["histogram"]=[{"label":f"{edges[i]:g}–{edges[i+1]:g}","count":int(counts[i])} for i in range(len(counts))]
    return jsonify(profile)

@cleaning_bp.post("/cleaning/edit")
def cleaning_edit():
    data=request.get_json(silent=True) or {}
    try: row=int(data.get("row"))
    except (TypeError,ValueError): return jsonify({"error":"Invalid row index."}),400
    column=data.get("column")
    if not isinstance(column,str): return jsonify({"error":"Invalid column."}),400
    path=_ensure_working()
    if not path: return jsonify({"error":"Upload a dataset first."}),400
    df=pd.read_csv(path)
    if column not in df.columns or row<0 or row>=len(df): return jsonify({"error":"Cell not found."}),404
    undo=os.path.join(os.path.dirname(path),f"undo_{uuid.uuid4().hex}.csv")
    shutil.copy2(path,undo)
    value=data.get("value","")
    df.at[row,column]=value if value!="" else np.nan
    df.to_csv(path,index=False)
    session["cleaning_undo_path"]=undo
    return jsonify({"success":True,"value":"" if pd.isna(df.at[row,column]) else str(df.at[row,column])})

@cleaning_bp.post("/cleaning/undo")
def cleaning_undo():
    path=session.get("cleaning_working_path")
    undo=session.get("cleaning_undo_path")
    if not path or not undo or not os.path.exists(path) or not os.path.exists(undo):
        return jsonify({"error":"No edit available to undo."}),400
    shutil.copy2(undo,path)
    os.remove(undo)
    session["cleaning_undo_path"]=None
    return jsonify({"success":True})

@cleaning_bp.post("/cleaning/reset")
def cleaning_reset():
    path=session.get("cleaning_working_path")
    if path and os.path.exists(path): os.remove(path)
    undo=session.get("cleaning_undo_path")
    if undo and os.path.exists(undo): os.remove(undo)
    session.pop("cleaning_working_path",None)
    session.pop("cleaning_undo_path",None)
    return jsonify({"success":True})

@cleaning_bp.get("/cleaning/export")
def cleaning_export():
    df = _read_working()
    if df is None: return jsonify({"error":"Upload a dataset first."}),400
    out_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)),"outputs")
    os.makedirs(out_dir,exist_ok=True)
    path=os.path.join(out_dir,f"dataqual_export_{uuid.uuid4().hex}.csv")
    df.to_csv(path,index=False)
    return send_file(path,as_attachment=True,download_name="dataqual_working_dataset.csv")

@cleaning_bp.post("/cleaning/export-selected")
def cleaning_export_selected():
    df = _read_working()
    if df is None: return jsonify({"error":"Upload a dataset first."}),400
    data=request.get_json(silent=True) or {}
    try: indexes=sorted({int(x) for x in data.get("rows",[])})
    except (TypeError,ValueError): return jsonify({"error":"Invalid row selection."}),400
    indexes=[i for i in indexes if i in df.index]
    if not indexes: return jsonify({"error":"Select at least one row."}),400
    out_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)),"outputs")
    os.makedirs(out_dir,exist_ok=True)
    path=os.path.join(out_dir,f"dataqual_selected_{uuid.uuid4().hex}.csv")
    df.loc[indexes].to_csv(path,index=False)
    return send_file(path,as_attachment=True,download_name="dataqual_selected_rows.csv")

@cleaning_bp.post("/cleaning/apply")
def cleaning_apply():
    df, filename = _read_current()
    if df is None:
        flash("Upload a dataset before cleaning.", "error")
        return redirect(url_for("cleaning.cleaning_page"))
    operations = _operations()
    if not operations:
        flash("Choose at least one cleaning operation.", "error")
        return redirect(url_for("cleaning.cleaning_page"))
    working = _read_working()
    cleaned = _clean(working if working is not None else df, operations)
    out_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)),"outputs")
    os.makedirs(out_dir,exist_ok=True)
    out_path=os.path.join(out_dir,f"cleaned_{uuid.uuid4().hex}.csv")
    cleaned.to_csv(out_path,index=False)
    session["cleaning_output_path"]=out_path
    session["cleaning_output_name"]=f"cleaned_{os.path.splitext(filename)[0]}.csv"
    session["cleaning_output_rows"]=len(cleaned)
    session["cleaning_output_operations"]=operations
    flash("Cleaning applied to a separate copy. Your original upload is unchanged.","success")
    return redirect(url_for("cleaning.cleaning_page"))

@cleaning_bp.get("/cleaning/download")
def cleaning_download():
    path=session.get("cleaning_output_path")
    if not path or not os.path.exists(path):
        flash("Apply cleaning operations first.","error")
        return redirect(url_for("cleaning.cleaning_page"))
    return send_file(path,as_attachment=True,download_name=session.get("cleaning_output_name","cleaned_dataset.csv"))
