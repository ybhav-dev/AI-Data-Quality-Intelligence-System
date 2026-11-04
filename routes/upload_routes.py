import os
import uuid
import pandas as pd
from flask import Blueprint, current_app, jsonify, request, session
from services.data_profiler import profile_dataset

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}

@upload_bp.post("/api/upload")
def upload_dataset():
    if "dataset" not in request.files:
        return jsonify({"error": "Please choose a dataset file."}), 400

    file = request.files["dataset"]
    if not file.filename:
        return jsonify({"error": "Please choose a dataset file."}), 400

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Unsupported file type. Upload CSV or Excel."}), 400

    safe_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(current_app.root_path, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, safe_name)
    file.save(path)
    session["latest_dataset_path"] = path
    session["latest_dataset_name"] = file.filename
    # A new upload starts a fresh cleaning workspace and output.
    for key in ("cleaning_working_path", "cleaning_undo_path", "cleaning_output_path",
                "cleaning_output_name", "cleaning_output_rows", "cleaning_output_operations"):
        session.pop(key, None)

    try:
        if ext == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
        if df.empty:
            return jsonify({"error": "The uploaded dataset is empty."}), 400
        result = profile_dataset(df, file.filename)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"Could not read this file. Please check its format. ({str(exc)[:160]})"}), 400
