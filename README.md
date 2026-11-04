# AI Data Quality Intelligence System

A Flask-based application for analyzing dataset quality and assisting with data cleaning.

## Run locally
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Theme
- Cherry Cola: `#9A0002`
- Cream Vanilla: `#EFE6DE`
\n## Current features\n- Dashboard UI with Cherry Cola / Cream Vanilla theme\n- CSV and Excel upload endpoint\n- Initial profiling for row/column count, missing values, duplicates, and quality dimensions\n\n## Data quality checks (current milestone)\n- Missing and placeholder values\n- Duplicate rows\n- Email, date, age, rating, quantity and negative price/amount validation\n- City/state mismatch and basic formatting consistency checks\n- Isolation Forest-based numeric anomaly flagging\n- Quality score dimensions and issue counts\n
## Detailed Data Analysis page\n- Open /analysis after uploading a dataset\n- Browse findings by issue type and search across row, column, value, and reason\n- Dataset metadata is held in the Flask session for the local workflow\n


