import os
import uuid
import pandas as pd
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, send_file, flash
from services.ai_recommendations import build_recommendations, apply_recommendations

recommendations_bp = Blueprint("recommendations", __name__)

def _read_dataset(path):
    ext = os.path.splitext(path.lower())[1]
    return pd.read_csv(path) if ext == ".csv" else pd.read_excel(path)

def _current():
    path = session.get("latest_dataset_path")
    if not path or not os.path.exists(path):
        return None, None
    return _read_dataset(path), session.get("latest_dataset_name", "Dataset")

@recommendations_bp.get("/recommendations")
def recommendations_page():
    df, filename = _current()
    if df is None:
        return render_template("recommendations.html", has_dataset=False, filename=None, recommendations=[])
    recommendations = build_recommendations(df)
    return render_template("recommendations.html", has_dataset=True, filename=filename,
                           rows=len(df), recommendations=recommendations,
                           cleaned_ready=bool(session.get("cleaned_dataset_path")))

@recommendations_bp.post("/recommendations/preview")
def preview_recommendations():
    df, filename = _current()
    if df is None:
        return jsonify({"error": "Upload a dataset first."}), 400
    selected = request.form.getlist("recommendations")
    recs = build_recommendations(df)
    cleaned = apply_recommendations(df, selected, recs)
    return jsonify({
        "before_rows": int(len(df)), "after_rows": int(len(cleaned)),
        "before_missing": int(df.isna().sum().sum()), "after_missing": int(cleaned.isna().sum().sum()),
        "selected_count": len(selected), "columns": list(map(str, cleaned.columns)),
        "preview": cleaned.head(8).where(pd.notna(cleaned.head(8)), "").to_dict(orient="records")
    })

@recommendations_bp.post("/recommendations/apply")
def apply_selected():
    df, filename = _current()
    if df is None:
        flash("Upload a dataset before applying recommendations.", "error")
        return redirect(url_for("recommendations.recommendations_page"))
    selected = request.form.getlist("recommendations")
    recs = build_recommendations(df)
    cleaned = apply_recommendations(df, selected, recs)
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"cleaned_{uuid.uuid4().hex}.csv")
    cleaned.to_csv(out_path, index=False)
    session["cleaned_dataset_path"] = out_path
    session["cleaned_dataset_name"] = f"cleaned_{filename.rsplit('.',1)[0]}.csv"
    flash(f"Applied {len(selected)} selected recommendation(s). Your original file is unchanged.", "success")
    return redirect(url_for("recommendations.recommendations_page"))

@recommendations_bp.get("/recommendations/download")
def download_cleaned():
    path = session.get("cleaned_dataset_path")
    if not path or not os.path.exists(path):
        flash("Apply recommendations first to create a cleaned file.", "error")
        return redirect(url_for("recommendations.recommendations_page"))
    return send_file(path, as_attachment=True, download_name=session.get("cleaned_dataset_name","cleaned_dataset.csv"))
